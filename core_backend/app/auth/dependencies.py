"""This module contains authentication dependencies for the FastAPI application."""

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.requests import Request
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import CHECK_API_LIMIT, DEFAULT_API_QUOTA, DEFAULT_CONTENT_QUOTA
from ..database import get_sqlalchemy_async_engine
from ..users.models import (
    UserDB,
    UserNotFoundError,
    WorkspaceDB,
    WorkspaceNotFoundError,
    add_user_workspace_role,
    create_workspace,
    get_user_by_username,
    get_workspace_by_workspace_name,
    save_user_to_db,
)
from ..users.schemas import UserCreate, UserRoles
from ..utils import (
    get_key_hash,
    setup_logger,
    update_api_limits,
    verify_password_salted_hash,
)
from .config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET,
    REDIS_KEY_EXPIRED,
)
from .schemas import AuthenticatedUser

logger = setup_logger()

bearer = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


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
        Authenticated user if the user is authenticated, otherwise None.
    """

    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        try:
            user_db = await get_user_by_username(asession=asession, username=username)
            if verify_password_salted_hash(password, user_db.hashed_password):
                # Hardcode "fullaccess" now, but may use it in the future.
                return AuthenticatedUser(access_level="fullaccess", username=username)
            return None
        except UserNotFoundError:
            return None


async def authenticate_or_create_google_user(
    *, google_email: str, request: Request
) -> AuthenticatedUser | None:
    """Check if user exists in the `UserDB` database. If not, create the `UserDB`
    object.

    NB: When a Google user is created, their workspace name defaults to 
    `Workspace_{google_email}` with a default role of ADMIN.

    Parameters
    ----------
    google_email
        Google email address.
    request
        The request object.

    Returns
    -------
    AuthenticatedUser | None
        Authenticated user if the user is authenticated or a new user is created. None
        if a new user is being created and the requested workspace already exists.
    """

    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        try:
            user_db = await get_user_by_username(
                asession=asession, username=google_email
            )
            return AuthenticatedUser(
                access_level="fullaccess", username=user_db.username
            )
        except UserNotFoundError:
            # Create the new user object with the specified role and workspace name.
            workspace_name = f"Workspace_{google_email}"
            user = UserCreate(
                role=UserRoles.ADMIN,
                username=google_email,
                workspace_name=workspace_name,
            )

            # Create the default workspace for the Google user.
            try:
                _ = await get_workspace_by_workspace_name(
                    asession=asession, workspace_name=workspace_name
                )
                return None
            except WorkspaceNotFoundError:
                workspace_db_new = await create_workspace(
                    api_daily_quota=DEFAULT_API_QUOTA,
                    asession=asession,
                    content_quota=DEFAULT_CONTENT_QUOTA,
                    user=user,
                )

            # Save the user to the `UserDB` database.
            user_db = await save_user_to_db(asession=asession, user=user)

            # Assign user to the specified workspace with the specified role.
            _ = await add_user_workspace_role(
                asession=asession,
                user_db=user_db,
                user_role=user.role,
                workspace_db=workspace_db_new,
            )

            await update_api_limits(
                api_daily_quota=DEFAULT_API_QUOTA,
                redis=request.app.state.redis,
                workspace_name=workspace_db_new.workspace_name,
            )
            return AuthenticatedUser(
                access_level="fullaccess", username=user_db.username
            )


def create_access_token(*, username: str) -> str:
    """Create an access token for the user.

    Parameters
    ----------
    username
        The username of the user to create the access token for.

    Returns
    -------
    str
        The access token.
    """

    payload: dict[str, str | datetime] = {}
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload["exp"] = expire
    payload["iat"] = datetime.now(timezone.utc)
    payload["sub"] = username
    payload["type"] = "access_token"

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)



async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserDB:
    """Get the current user from the access token.

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
    HTTPException
        If the credentials are invalid.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception

        # Fetch user from database.
        async with AsyncSession(
            get_sqlalchemy_async_engine(), expire_on_commit=False
        ) as asession:
            try:
                user_db = await get_user_by_username(
                    asession=asession, username=username
                )
                return user_db
            except UserNotFoundError as err:
                raise credentials_exception from err
    except InvalidTokenError as err:
        raise credentials_exception from err


async def get_current_workspace(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> WorkspaceDB:
    """Get the current workspace from the access token.

    Parameters
    ----------
    token
        The access token.

    Returns
    -------
    WorkspaceDB
        The workspace object.

    Raises
    ------
    HTTPException
        If the credentials are invalid.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception

        # HACK FIX FOR FRONTEND
        if username in ["tony", "mark"]:
            workspace_name = "Workspace_DEFAULT"
        elif username in ["carlos", "amir", "sid"]:
            workspace_name = "Workspace_1"
        else:
            workspace_name = None
        if workspace_name is None:
            raise credentials_exception

        # Fetch workspace from database.
        async with AsyncSession(
            get_sqlalchemy_async_engine(), expire_on_commit=False
        ) as asession:
            try:
                workspace_db = await get_workspace_by_workspace_name(
                    asession=asession, workspace_name=workspace_name
                )
                return workspace_db
            except WorkspaceNotFoundError as err:
                raise credentials_exception from err
    except InvalidTokenError as err:
        raise credentials_exception from err


# XXX
async def authenticate_key(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> UserDB:
    """Authenticate using basic bearer token. Used for calling the question-answering
    endpoints. In case the JWT token is provided instead of the API key, it will fall
    back to the JWT token authentication.

    Parameters
    ----------
    credentials
        The bearer token.

    Returns
    -------
    UserDB
        The user object.
    """

    token = credentials.credentials
    print("authenticate_key")
    print(f"{token = }")
    input()
    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        try:
            user_db = await get_user_by_api_key(token, asession)
            return user_db
        except UserNotFoundError:
            # Fall back to JWT token authentication if api key is not valid.
            user_db = await get_current_user(token)
            return user_db


async def get_user_by_api_key(*, asession: AsyncSession, token: str) -> UserDB:
    """Retrieve a user by token.

    Parameters
    ----------
    asession
        The async session to use for the database connection.
    token
        The token to use for the query.

    Returns
    -------
    UserDB
        The user object retrieved from the database.

    Raises
    ------
    UserNotFoundError
        If the user with the specified token does not exist.
    """

    print(f"get_user_by_api_key: {token = }")
    input()
    hashed_token = get_key_hash(token)

    stmt = select(UserDB).where(UserDB.hashed_api_key == hashed_token)
    result = await asession.execute(stmt)
    try:
        user = result.scalar_one()
        return user
    except NoResultFound as err:
        raise UserNotFoundError("User with given token does not exist.") from err


async def rate_limiter(
    request: Request,
    user_db: UserDB = Depends(authenticate_key),
) -> None:
    """
    Rate limiter for the API calls. Gets daily quota and decrement it
    """

    print(f"rate_limiter: {user_db = }")
    input()

    if CHECK_API_LIMIT is False:
        return
    username = user_db.username
    key = f"remaining-calls:{username}"
    redis = request.app.state.redis
    ttl = await redis.ttl(key)
    # if key does not exist, set the key and value
    if ttl == REDIS_KEY_EXPIRED:
        await update_api_limits(redis, username, user_db.api_daily_quota)

    nb_remaining = await redis.get(key)

    if nb_remaining != b"None":
        nb_remaining = int(nb_remaining)
        if nb_remaining <= 0:
            raise HTTPException(status_code=429, detail="API call limit reached.")
        await update_api_limits(redis, username, nb_remaining - 1)
