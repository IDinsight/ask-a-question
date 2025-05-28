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

from ..config import CHECK_API_LIMIT
from ..database import get_sqlalchemy_async_engine
from ..users.models import (
    UserDB,
    UserNotFoundError,
    WorkspaceDB,
    get_user_by_username,
    get_user_default_workspace,
    get_user_role_in_workspace,
)
from ..users.schemas import UserRoles
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


class WorkspaceTokenNotFoundError(Exception):
    """Exception raised when a workspace token is not found in the `WorkspaceDB`
    database.
    """


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
            if verify_password_salted_hash(
                key=password, stored_hash=user_db.hashed_password
            ):
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
            return None
        except UserNotFoundError:
            return None


async def authenticate_key(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> WorkspaceDB:
    """Authenticate using basic bearer token. This is used by endpoints such as:

    1. Data API
    2. Question answering
    3. Urgency detection

    In case the JWT token is provided instead of the API key, it will fall back to the
    JWT token authentication.

    Parameters
    ----------
    credentials
        The bearer token.

    Returns˜
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

    def _get_username_and_workspace_name_from_token(
        *, token_: Annotated[str, Depends(oauth2_scheme)]
    ) -> tuple[str, str]:
        """Get username and workspace name from the JWT token.

        Parameters
        ----------
        token_
            The JWT token.

        Returns
        -------
        tuple[str, str]
            The username and workspace name.

        Raises
        ------
        HTTPException
            If the credentials are invalid.
        """

        try:
            payload = jwt.decode(token_, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            username_ = payload.get("username", None)
            workspace_name_ = payload.get("workspace_name", None)
            if not (username_ and workspace_name_):
                raise credentials_exception
            return username_, workspace_name_
        except InvalidTokenError as e:
            raise credentials_exception from e

    token = credentials.credentials
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
            _, workspace_name = _get_username_and_workspace_name_from_token(
                token_=token
            )
            stmt = select(WorkspaceDB).where(
                WorkspaceDB.workspace_name == workspace_name
            )
            result = await asession.execute(stmt)
            try:
                workspace_db = result.scalar_one()
                return workspace_db
            except NoResultFound as err:
                raise credentials_exception from err


def create_access_token(
    *, user_role: UserRoles, username: str, workspace_name: str
) -> str:
    """Create an access token for the user.

    Parameters
    ----------
    user_role
        The role of the user.
    username
        The username of the user to create the access token for.
    workspace_name
        The name of the workspace selected for the user.

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
    payload["type"] = "access_token"
    payload["user_role"] = user_role
    payload["username"] = username
    payload["workspace_name"] = workspace_name

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserDB:
    """Get the current user from the access token.

    NB: We have to check that both the username and workspace name are present in the
    payload. If either one is missing, then this corresponds to the situation where
    there are neither users nor workspaces present.

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
        username = payload.get("username", None)
        workspace_name = payload.get("workspace_name", None)
        if not (username and workspace_name):
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


async def get_current_workspace_name(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> str:
    """Get the current workspace name from the access token.

    NB: We have to check that both the username and workspace name are present in the
    payload. If either one is missing, then this corresponds to the situation where
    there are neither users nor workspaces present.

    NB: The workspace object cannot be retrieved in this module due to circular imports.
    Instead, the workspace name is retrieved from the payload and the caller is
    responsible for retrieving the workspace object.

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
        username = payload.get("username", None)
        workspace_name = payload.get("workspace_name", None)
        if not (username and workspace_name):
            raise credentials_exception
        return workspace_name
    except InvalidTokenError as err:
        raise credentials_exception from err


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


async def rate_limiter(
    request: Request, workspace_db: WorkspaceDB = Depends(authenticate_key)
) -> None:
    """Rate limiter for the API calls. Gets daily quota and decrement it.

    This is used by the following packages:

    1. Question answering
    2. Urgency detection

    Parameters
    ----------
    request
        The request object.
    workspace_db
        The workspace object.

    Raises
    ------
    HTTPException
        If the API call limit is reached.
    RuntimeError
        If the user belongs to multiple workspaces.
    """

    if CHECK_API_LIMIT is False:
        return

    workspace_name = workspace_db.workspace_name
    key = f"remaining-calls:{workspace_name}"
    redis = request.app.state.redis
    ttl = await redis.ttl(key)

    # If key does not exist, set the key and value.
    if ttl == REDIS_KEY_EXPIRED:
        await update_api_limits(
            api_daily_quota=workspace_db.api_daily_quota,
            redis=redis,
            workspace_name=workspace_name,
        )

    nb_remaining = await redis.get(key)

    if nb_remaining != b"None":
        nb_remaining = int(nb_remaining)
        if nb_remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"API call limit reached for workspace: {workspace_name}.",
            )
        await update_api_limits(
            api_daily_quota=nb_remaining - 1, redis=redis, workspace_name=workspace_name
        )
