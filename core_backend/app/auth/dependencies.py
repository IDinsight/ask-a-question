from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict, Optional, Union

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.requests import Request
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import CHECK_API_LIMIT, DEFAULT_API_QUOTA, DEFAULT_CONTENT_QUOTA
from ..database import get_sqlalchemy_async_engine
from ..users.models import (
    UserDB,
    UserNotFoundError,
    add_user_workspace_role,
    create_workspace,
    get_user_by_api_key,
    get_user_by_username,
    save_user_to_db,
)
from ..users.schemas import UserCreate, UserRoles
from ..utils import (
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


async def authenticate_credentials(
    *, password: str, username: str
) -> Optional[AuthenticatedUser]:
    """Authenticate user using username and password.

    Parameters
    ----------
    password
        User password.
    username
        User username.

    Returns
    -------
    Optional[AuthenticatedUser]
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
    *,
    google_email: str,
    request: Request,
    user_role: UserRoles,
    workspace_name: Optional[str] = None,
) -> AuthenticatedUser:
    """Check if user exists in the `UserDB` table. If not, create the `UserDB` object.

    Parameters
    ----------
    google_email
        Google email address.
    request
        The request object.
    user_role
        The user role to assign to the Google login user.
    workspace_name
        The workspace name to create for the Google login user. If not specified, then
        the default workspace name is the next available workspace ID.

    Returns
    -------
    AuthenticatedUser
        The authenticated user object.
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
            user = UserCreate(username=google_email)
            user_db = await save_user_to_db(asession=asession, user=user)

            # Create the workspace.
            workspace_new = await create_workspace(
                api_daily_quota=DEFAULT_API_QUOTA,
                asession=asession,
                content_quota=DEFAULT_CONTENT_QUOTA,
                workspace_name=workspace_name,
            )

            # Assign user to the specified workspace with the specified role.
            _ = await add_user_workspace_role(
                asession=asession,
                user=user_db,
                user_role=user_role,
                workspace=workspace_new,
            )

            await update_api_limits(
                api_daily_quota=DEFAULT_API_QUOTA,
                redis=request.app.state.redis,
                workspace_name=workspace_new.workspace_name,
            )
            return AuthenticatedUser(
                access_level="fullaccess", username=user_db.username
            )


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserDB:
    """
    Get the current user from the access token
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

        # fetch user from database
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


def create_access_token(username: str) -> str:
    """
    Create an access token for the user
    """
    payload: Dict[str, Union[str, datetime]] = {}
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload["exp"] = expire
    payload["iat"] = datetime.now(timezone.utc)
    payload["sub"] = username
    payload["type"] = "access_token"

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def rate_limiter(
    request: Request,
    user_db: UserDB = Depends(authenticate_key),
) -> None:
    """
    Rate limiter for the API calls. Gets daily quota and decrement it
    """
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
