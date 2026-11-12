"""This module contains the business logic for user and workspace authentication.

The FastAPI dependency functions in `app.auth.router` extract tokens/credentials from
the request and delegate to the functions here. Functions in this module never raise
`HTTPException`; they raise the domain exceptions in `app.core.exceptions` instead.
"""

from typing import Any
from uuid import uuid4

import jwt
from google.auth.transport import requests
from google.oauth2 import id_token
from jwt.exceptions import InvalidTokenError
from redis import asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import AccessLevel, AuthenticatedUser, AuthenticationDetails
from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    CHECK_API_LIMIT,
    DEFAULT_API_QUOTA,
    DEFAULT_CONTENT_QUOTA,
    DEFAULT_DOC_LANGUAGE,
    JWT_ALGORITHM,
    JWT_SECRET,
    NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID,
    REDIS_KEY_EXPIRED,
    REFRESH_TOKEN_EXPIRE_MINUTES,
)
from app.core.database import get_sqlalchemy_async_engine
from app.core.exceptions import (
    BadRequestError,
    TooManyRequestsError,
    UnauthorizedError,
)
from app.core.observability import setup_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_key_hash,
    update_api_limits,
    verify_dummy_password,
    verify_password,
)
from app.users.models import UserDB
from app.users.repository import (
    UserNotFoundError,
    create_user_workspace_role,
    get_user_by_username,
    get_user_default_workspace,
    get_user_role_in_workspace,
    save_user_to_db,
    update_user_hashed_password,
)
from app.users.schemas import UserCreate, UserRoles
from app.workspaces.models import WorkspaceDB
from app.workspaces.repository import create_workspace

logger = setup_logger()

# Issuers accepted for Google ID tokens.
GOOGLE_TOKEN_ISSUERS = ["accounts.google.com", "https://accounts.google.com"]


class WorkspaceTokenNotFoundError(Exception):
    """Exception raised when a workspace token is not found in the `WorkspaceDB`
    database.
    """


def _credentials_error() -> UnauthorizedError:
    """Build the 401 error returned whenever a bearer token cannot be validated.

    Returns
    -------
    UnauthorizedError
        The error with the same detail and `WWW-Authenticate` header that the
        original `HTTPException` carried.
    """

    return UnauthorizedError(
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode_token(*, expected_type: str, token: str) -> dict[str, Any]:
    """Verify a JWT issued by this app and check it is of the expected type.

    The `type` check stops a refresh token being used as an access token (and the
    other way round), since both are signed with the same secret.

    NB: We have to check that both the username and workspace name are present in the
    payload. If either one is missing, then this corresponds to the situation where
    there are neither users nor workspaces present.

    Parameters
    ----------
    expected_type
        The required `type` claim ("access_token" or "refresh_token").
    token
        The JWT token.

    Returns
    -------
    dict[str, Any]
        The verified payload. `username` and `workspace_name` are non-empty strings.

    Raises
    ------
    UnauthorizedError
        If the token is invalid, expired, of the wrong type or missing claims.
    """

    try:
        # Pin the algorithm list (never trust the token header) and require the time
        # claims, so a token without `exp` cannot live forever.
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat"]},
        )
    except InvalidTokenError as err:
        raise _credentials_error() from err

    if payload.get("type") != expected_type:
        raise _credentials_error()

    username = payload.get("username", None)
    workspace_name = payload.get("workspace_name", None)
    if not (
        isinstance(username, str)
        and username
        and isinstance(workspace_name, str)
        and workspace_name
    ):
        raise _credentials_error()
    return payload


def decode_access_token(*, token: str) -> tuple[str, str]:
    """Get username and workspace name from a JWT access token.

    Parameters
    ----------
    token
        The JWT token.

    Returns
    -------
    tuple[str, str]
        The username and workspace name.

    Raises
    ------
    UnauthorizedError
        If the credentials are invalid.
    """

    payload = _decode_token(expected_type="access_token", token=token)
    return payload["username"], payload["workspace_name"]


# ---------------------------------------------------------------------------
# Refresh tokens.
#
# A refresh token is a signed JWT plus Redis state, so it can be revoked:
#
#   refresh-token:<jti>         exists until the token is used (single use)
#   refresh-family:<family id>  exists while the login session is valid
#   refresh-user:<username>     set of the user's family ids (to revoke them all)
#
# Every refresh deletes the presented token and issues a new one in the same family
# (rotation). Presenting a token that was already used means it was copied, so the
# whole family is revoked and both the thief and the user must log in again.
# ---------------------------------------------------------------------------

REFRESH_TOKEN_TTL_SECONDS = REFRESH_TOKEN_EXPIRE_MINUTES * 60


def _refresh_token_key(token_id: str) -> str:
    """Redis key marking a refresh token as unused."""

    return f"refresh-token:{token_id}"


def _refresh_family_key(family_id: str) -> str:
    """Redis key marking a refresh token family (login session) as valid."""

    return f"refresh-family:{family_id}"


def _refresh_user_key(username: str) -> str:
    """Redis key holding the set of a user's refresh token family ids."""

    return f"refresh-user:{username}"


async def issue_refresh_token(
    *,
    family_id: str | None = None,
    redis: aioredis.Redis,
    username: str,
    workspace_name: str,
) -> str:
    """Create a refresh token and register it in Redis.

    Parameters
    ----------
    family_id
        The family to add the token to. `None` starts a new family (a new login).
    redis
        The Redis client holding refresh token state.
    username
        The username the token is issued to.
    workspace_name
        The workspace the token is scoped to.

    Returns
    -------
    str
        The encoded refresh token.
    """

    family_id = family_id or uuid4().hex
    token_id = uuid4().hex
    ttl = REFRESH_TOKEN_TTL_SECONDS

    # One round trip. Each refresh slides the family's expiry forward, so a session
    # ends after REFRESH_TOKEN_EXPIRE_MINUTES without activity.
    async with redis.pipeline(transaction=True) as pipe:
        pipe.set(_refresh_token_key(token_id), family_id, ex=ttl)
        pipe.set(_refresh_family_key(family_id), username, ex=ttl)
        pipe.sadd(_refresh_user_key(username), family_id)
        pipe.expire(_refresh_user_key(username), ttl)
        await pipe.execute()

    return create_refresh_token(
        family_id=family_id,
        token_id=token_id,
        username=username,
        workspace_name=workspace_name,
    )


async def revoke_refresh_token_family(
    *, family_id: str, redis: aioredis.Redis, username: str
) -> None:
    """Revoke every refresh token issued from one login.

    Parameters
    ----------
    family_id
        The family to revoke.
    redis
        The Redis client holding refresh token state.
    username
        The family's user.
    """

    async with redis.pipeline(transaction=True) as pipe:
        pipe.delete(_refresh_family_key(family_id))
        pipe.srem(_refresh_user_key(username), family_id)
        await pipe.execute()


async def revoke_all_refresh_tokens(*, redis: aioredis.Redis, username: str) -> None:
    """Revoke every refresh token of a user, e.g. after a password reset. Access
    tokens already issued stay valid until they expire (ACCESS_TOKEN_EXPIRE_MINUTES).

    Parameters
    ----------
    redis
        The Redis client holding refresh token state.
    username
        The user whose sessions are revoked.
    """

    user_key = _refresh_user_key(username)
    # redis-py types smembers as "Awaitable[set] | set" for its sync and async clients.
    family_ids: set[bytes] = await redis.smembers(user_key)  # type: ignore[misc]
    keys = [_refresh_family_key(f.decode()) for f in family_ids] + [user_key]
    await redis.delete(*keys)


async def refresh_access_token(
    *, redis: aioredis.Redis, refresh_token: str
) -> AuthenticationDetails:
    """Exchange a refresh token for a new access token and refresh token.

    The process is as follows:

    1. Verify the JWT (signature, expiry, `type`).
    2. Consume the token in Redis. Deleting the key is atomic, so of two concurrent
        refreshes with the same token only one succeeds.
    3. If the token was already consumed, it is being reused: revoke its family.
    4. Check the family has not been revoked (logout, reuse, password reset).
    5. Check the user still exists and is still in the workspace, and re-read their
        role, so removals and role changes apply at the next refresh.
    6. Issue a new pair in the same family.

    Parameters
    ----------
    redis
        The Redis client holding refresh token state.
    refresh_token
        The refresh token sent by the client.

    Returns
    -------
    AuthenticationDetails
        The new access token and refresh token.

    Raises
    ------
    UnauthorizedError
        If the refresh token is invalid, already used, revoked, or its user no
        longer belongs to the workspace.
    """

    # 1.
    payload = _decode_token(expected_type="refresh_token", token=refresh_token)
    username: str = payload["username"]
    workspace_name: str = payload["workspace_name"]
    token_id = payload.get("jti")
    family_id = payload.get("fam")
    if not (isinstance(token_id, str) and isinstance(family_id, str)):
        raise _credentials_error()

    # 2.
    consumed = await redis.delete(_refresh_token_key(token_id))

    # 3.
    if not consumed:
        logger.warning(
            "Refresh token reuse detected; revoking its session family.",
        )
        await revoke_refresh_token_family(
            family_id=family_id, redis=redis, username=username
        )
        raise _credentials_error()

    # 4.
    if not await redis.exists(_refresh_family_key(family_id)):
        raise _credentials_error()

    # 5.
    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        _, user_role = await _get_membership(
            asession=asession, username=username, workspace_name=workspace_name
        )

    # 6.
    return await build_authentication_details(
        access_level="fullaccess",
        family_id=family_id,
        redis=redis,
        user_role=user_role,
        username=username,
        workspace_name=workspace_name,
    )


async def logout(*, redis: aioredis.Redis, refresh_token: str) -> None:
    """Revoke the login session a refresh token belongs to.

    Logging out always succeeds from the client's point of view: an invalid or
    expired token has nothing left to revoke.

    Parameters
    ----------
    redis
        The Redis client holding refresh token state.
    refresh_token
        The refresh token sent by the client.
    """

    try:
        payload = _decode_token(expected_type="refresh_token", token=refresh_token)
    except UnauthorizedError:
        return
    family_id = payload.get("fam")
    if isinstance(family_id, str):
        await revoke_refresh_token_family(
            family_id=family_id, redis=redis, username=payload["username"]
        )


async def build_authentication_details(
    *,
    access_level: AccessLevel,
    family_id: str | None = None,
    redis: aioredis.Redis,
    user_role: UserRoles,
    username: str,
    workspace_name: str,
) -> AuthenticationDetails:
    """Issue an access token and refresh token for the user in the given workspace
    and wrap them in the response model returned by the login, refresh and
    workspace-switch endpoints.

    Parameters
    ----------
    access_level
        The access level of the user.
    family_id
        The refresh token family to continue (on refresh). `None` starts a new one.
    redis
        The Redis client holding refresh token state.
    user_role
        The role of the user in the workspace.
    username
        The username of the user.
    workspace_name
        The name of the workspace the token is scoped to.

    Returns
    -------
    AuthenticationDetails
        A Pydantic model containing the JWT token, token type, access level, and
        username.
    """

    return AuthenticationDetails(
        access_level=access_level,
        access_token=create_access_token(
            user_role=user_role, username=username, workspace_name=workspace_name
        ),
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=await issue_refresh_token(
            family_id=family_id,
            redis=redis,
            username=username,
            workspace_name=workspace_name,
        ),
        # "bearer" is the OAuth2 token type name, not a secret.
        token_type="bearer",  # nosec B106
        user_role=user_role,
        username=username,
        workspace_name=workspace_name,
    )


async def authenticate_credentials(
    *, password: str, username: str
) -> AuthenticatedUser | None:
    """Authenticate user using username and password.

    Parameters
    ----------
    password
        User password.
    username
        User username.

    Returns
    -------
    AuthenticatedUser | None
        Authenticated user if the user is authenticated, otherwise `None`.
    """

    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        try:
            user_db = await get_user_by_username(asession=asession, username=username)
        except UserNotFoundError:
            # Do the same Argon2 work as for a real user, so response time does not
            # reveal whether the username exists.
            verify_dummy_password(password=password)
            return None

        is_valid, new_hash = verify_password(
            password=password, stored_hash=user_db.hashed_password
        )
        if not is_valid:
            return None

        # Legacy SHA-256 (or outdated Argon2) hash: replace it now that we have the
        # plaintext. This is how existing accounts migrate to Argon2.
        if new_hash is not None:
            await update_user_hashed_password(
                asession=asession, hashed_password=new_hash, user_db=user_db
            )

        user_workspace_db = await get_user_default_workspace(
            asession=asession, user_db=user_db
        )
        user_role = await get_user_role_in_workspace(
            asession=asession, user_db=user_db, workspace_db=user_workspace_db
        )
        assert user_role is not None and user_role in UserRoles

        # Hardcode "fullaccess" now, but may use it in the future.
        return AuthenticatedUser(
            access_level="fullaccess",
            user_role=user_role,
            username=username,
            workspace_name=user_workspace_db.workspace_name,
        )


async def login_with_credentials(
    *, password: str, redis: aioredis.Redis, username: str
) -> AuthenticationDetails:
    """Authenticate a user with username and password and issue a JWT token.

    Parameters
    ----------
    password
        User password.
    redis
        The Redis client holding refresh token state.
    username
        User username.

    Returns
    -------
    AuthenticationDetails
        A Pydantic model containing the JWT token, token type, access level, and
        username.

    Raises
    ------
    UnauthorizedError
        If the user credentials are invalid.
    """

    authenticated_user = await authenticate_credentials(
        password=password, username=username
    )

    if authenticated_user is None:
        raise UnauthorizedError("Invalid credentials.")

    return await build_authentication_details(
        redis=redis,
        access_level=authenticated_user.access_level,
        user_role=authenticated_user.user_role,
        username=authenticated_user.username,
        workspace_name=authenticated_user.workspace_name,
    )


def verify_google_token(*, credential: str) -> dict[str, Any]:
    """Verify a Google ID token and return its claims.

    Parameters
    ----------
    credential
        The Google ID token sent by the frontend.

    Returns
    -------
    dict[str, Any]
        The verified token claims (includes `email`).

    Raises
    ------
    UnauthorizedError
        If the Google token is invalid or was issued by an unexpected issuer.
    """

    try:
        idinfo = id_token.verify_oauth2_token(
            credential,
            requests.Request(),
            NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID,
        )
        if idinfo["iss"] not in GOOGLE_TOKEN_ISSUERS:
            raise ValueError("Wrong issuer.")
    except ValueError as e:
        raise UnauthorizedError("Invalid token.") from e
    return idinfo


async def login_with_google(
    *, credential: str, redis: aioredis.Redis
) -> AuthenticationDetails:
    """Verify a Google token, authenticate (or register) the Google user, and issue a
    JWT token for the user.

    Parameters
    ----------
    credential
        The Google ID token sent by the frontend.
    redis
        The Redis client used to initialize API limits for new workspaces.

    Returns
    -------
    AuthenticationDetails
        A Pydantic model containing the JWT token, token type, access level, and
        username.

    Raises
    ------
    UnauthorizedError
        If the Google token is invalid.
    BadRequestError
        If the workspace requested by the Google user already exists.
    """

    idinfo = verify_google_token(credential=credential)

    authenticated_user = await authenticate_or_create_google_user(
        gmail=idinfo["email"], redis=redis
    )

    return await build_authentication_details(
        redis=redis,
        access_level=authenticated_user.access_level,
        user_role=authenticated_user.user_role,
        username=authenticated_user.username,
        workspace_name=authenticated_user.workspace_name,
    )


async def authenticate_or_create_google_user(
    *, gmail: str, redis: aioredis.Redis
) -> AuthenticatedUser:
    """Authenticate or create a Google user. A Google user can belong to multiple
    workspaces (e.g., if the admin of a workspace adds the Google user to their
    workspace with the gmail as the username). However, if a Google user registers,
    then a unique workspace is created for the Google user using their gmail.

    The process is as follows:

    1. The default workspace name for Google users is f"{gmail}'s Workspace" (and the
        default username is the gmail, and the default role is ADMIN).
    2. Check if the user exists in `UserDB`.
    3. If the username already exists in `UserDB`, then a default workspace should
        have already been associated with the user.
    4. Check the user role in the workspace. If the authenticating user exists in the
       workspace, then we return the`AuthenticatedUser` model with the correct user's
       role in the workspace.
    5. If the user does not exist in `UserDB`, then this is the first time that the
        Google user is authenticating.
    6. We try to create the workspace using the default workspace name for the new
        user. If the default workspace name already exists, then we raise an exception.
        This corresponds to the situation where another user has already created a
        workspace under the same name and the Google user is signing in for the very
        time.
    7. Finally, we update the API limits for the new workspace, create the user in
        `UserDB`, and assign the user to the workspace with the role of ADMIN.

    Parameters
    ----------
    gmail
        The Gmail address of the Google user.
    redis
        The Redis client used to set the API limits for a newly created workspace.

    Returns
    -------
    AuthenticatedUser
        A Pydantic model containing the access level, username, and workspace name.

    Raises
    ------
    BadRequestError
        If the workspace requested by the Google user already exists.
    """

    # 1.
    workspace_name = f"{gmail}'s Workspace"

    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        # 2.
        try:
            user_db = await get_user_by_username(asession=asession, username=gmail)
        except UserNotFoundError:
            user_db = None

        if user_db is not None:
            # 3.
            workspace_db = await get_user_default_workspace(
                asession=asession, user_db=user_db
            )

            # 4.
            user_role = await get_user_role_in_workspace(
                asession=asession, user_db=user_db, workspace_db=workspace_db
            )
            assert user_role is not None and user_role in UserRoles, f"{user_role = }"
            return AuthenticatedUser(
                access_level="fullaccess",
                user_role=user_role,
                username=user_db.username,
                workspace_name=workspace_db.workspace_name,
            )

        # 5.
        user = UserCreate(
            role=UserRoles.ADMIN, username=gmail, workspace_name=workspace_name
        )
        user_role = user.role
        assert user_role is not None and user_role in UserRoles

        # 6.
        workspace_db, is_new_workspace = await create_workspace(
            api_daily_quota=DEFAULT_API_QUOTA,
            asession=asession,
            content_quota=DEFAULT_CONTENT_QUOTA,
            doc_language=DEFAULT_DOC_LANGUAGE,
            user=user,
        )
        if not is_new_workspace:
            raise BadRequestError(
                f"Workspace for '{gmail}' already exists. Contact the admin of "
                f"that workspace to create an account for you."
            )

        # 7.
        await update_api_limits(
            api_daily_quota=workspace_db.api_daily_quota,
            redis=redis,
            workspace_name=workspace_db.workspace_name,
        )
        user_db = await save_user_to_db(asession=asession, user=user)
        _ = await create_user_workspace_role(
            asession=asession,
            is_default_workspace=True,
            user_db=user_db,
            user_role=user_role,
            workspace_db=workspace_db,
        )

        return AuthenticatedUser(
            access_level="fullaccess",
            user_role=user_role,
            username=user_db.username,
            workspace_name=workspace_name,
        )


async def get_workspace_by_api_key(
    *, asession: AsyncSession, token: str
) -> WorkspaceDB:
    """Retrieve a workspace by token.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    token
        The token to use to retrieve the appropriate workspace.

    Returns
    -------
    WorkspaceDB
        The workspace object corresponding to the token.

    Raises
    ------
    WorkspaceTokenNotFoundError
        If the workspace with the specified token does not exist.
    """

    hashed_token = get_key_hash(key=token)
    stmt = select(WorkspaceDB).where(WorkspaceDB.hashed_api_key == hashed_token)
    result = await asession.execute(stmt)
    try:
        workspace_db = result.scalar_one()
        return workspace_db
    except NoResultFound as err:
        raise WorkspaceTokenNotFoundError(
            "Workspace with given token does not exist."
        ) from err


async def get_workspace_by_api_key_or_jwt(*, token: str) -> WorkspaceDB:
    """Resolve the workspace for a bearer token. The token is first treated as a
    workspace API key; if no workspace matches, it is treated as a user JWT and the
    workspace named in its payload is returned.

    Parameters
    ----------
    token
        The bearer token (workspace API key or user JWT).

    Returns
    -------
    WorkspaceDB
        The workspace object.

    Raises
    ------
    UnauthorizedError
        If the token is neither a valid API key nor a valid JWT for an existing
        workspace.
    """

    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        try:
            workspace_db = await get_workspace_by_api_key(
                asession=asession, token=token
            )
            return workspace_db
        except WorkspaceTokenNotFoundError:
            # Fall back to JWT token authentication if API key is not valid.
            username, workspace_name = decode_access_token(token=token)
            return await _get_workspace_for_member(
                asession=asession, username=username, workspace_name=workspace_name
            )


async def _get_workspace_for_member(
    *, asession: AsyncSession, username: str, workspace_name: str
) -> WorkspaceDB:
    """Return the token's workspace, but only while the token's user still exists and
    still belongs to that workspace. See `_get_membership`.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    username
        The `username` claim from the token.
    workspace_name
        The `workspace_name` claim from the token.

    Returns
    -------
    WorkspaceDB
        The workspace the user is a member of.

    Raises
    ------
    UnauthorizedError
        If the user or workspace no longer exists, or the user is no longer a
        member of the workspace.
    """

    workspace_db, _ = await _get_membership(
        asession=asession, username=username, workspace_name=workspace_name
    )
    return workspace_db


async def _get_membership(
    *, asession: AsyncSession, username: str, workspace_name: str
) -> tuple[WorkspaceDB, UserRoles]:
    """Return the token's workspace and the user's role in it, but only while the
    token's user still exists and still belongs to that workspace.

    A JWT stays cryptographically valid until it expires, so without this check a
    user who was deleted or removed from a workspace keeps access until expiry.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    username
        The `username` claim from the token.
    workspace_name
        The `workspace_name` claim from the token.

    Returns
    -------
    tuple[WorkspaceDB, UserRoles]
        The workspace the user is a member of, and the user's current role in it.

    Raises
    ------
    UnauthorizedError
        If the user or workspace no longer exists, or the user is no longer a
        member of the workspace.
    """

    try:
        user_db = await get_user_by_username(asession=asession, username=username)
    except UserNotFoundError as err:
        raise _credentials_error() from err

    stmt = select(WorkspaceDB).where(WorkspaceDB.workspace_name == workspace_name)
    workspace_db = (await asession.execute(stmt)).scalar_one_or_none()
    if workspace_db is None:
        raise _credentials_error()

    user_role = await get_user_role_in_workspace(
        asession=asession, user_db=user_db, workspace_db=workspace_db
    )
    if user_role is None:
        raise _credentials_error()

    return workspace_db, user_role


async def get_workspace_name_for_access_token(*, token: str) -> str:
    """Return the workspace name in a JWT after checking the user is still a member.

    Parameters
    ----------
    token
        The access token.

    Returns
    -------
    str
        The workspace name.

    Raises
    ------
    UnauthorizedError
        If the token is invalid, or its user is gone or no longer in the workspace.
    """

    username, workspace_name = decode_access_token(token=token)
    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        workspace_db = await _get_workspace_for_member(
            asession=asession, username=username, workspace_name=workspace_name
        )
    return workspace_db.workspace_name


async def get_user_by_access_token(*, token: str) -> UserDB:
    """Get the user referenced by a JWT access token.

    Parameters
    ----------
    token
        The access token.

    Returns
    -------
    UserDB
        The user object.

    Raises
    ------
    UnauthorizedError
        If the token is invalid or the user does not exist.
    """

    username, _ = decode_access_token(token=token)

    # Fetch user from database.
    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        try:
            user_db = await get_user_by_username(asession=asession, username=username)
            return user_db
        except UserNotFoundError as err:
            raise _credentials_error() from err


async def consume_api_quota(
    *, redis: aioredis.Redis, workspace_db: WorkspaceDB
) -> None:
    """Get the workspace's remaining daily API quota from Redis and decrement it.

    Parameters
    ----------
    redis
        The Redis client holding the remaining-calls counters.
    workspace_db
        The workspace object making the API call.

    Raises
    ------
    TooManyRequestsError
        If the API call limit is reached.
    """

    if CHECK_API_LIMIT is False:
        return

    workspace_name = workspace_db.workspace_name
    key = f"remaining-calls:{workspace_name}"
    ttl = await redis.ttl(key)

    # If key does not exist, set the key and value.
    if ttl == REDIS_KEY_EXPIRED:
        await update_api_limits(
            api_daily_quota=workspace_db.api_daily_quota,
            redis=redis,
            workspace_name=workspace_name,
        )

    nb_remaining = await redis.get(key)

    # A stored value of "None" means the workspace has no daily quota.
    if nb_remaining != b"None":
        nb_remaining = int(nb_remaining)
        if nb_remaining <= 0:
            raise TooManyRequestsError(
                f"API call limit reached for workspace: {workspace_name}."
            )
        await update_api_limits(
            api_daily_quota=nb_remaining - 1, redis=redis, workspace_name=workspace_name
        )
