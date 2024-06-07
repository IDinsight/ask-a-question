from datetime import datetime, timedelta
from typing import Annotated, Dict, Optional, Union

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_sqlalchemy_async_engine
from ..users.models import (
    UserDB,
    UserNotFoundError,
    get_user_by_token,
    get_user_by_username,
    save_user_to_db,
)
from ..users.schemas import UserCreate
from ..utils import setup_logger, verify_password_salted_hash
from .config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET
from .schemas import AuthenticatedUser

logger = setup_logger()

bearer = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def authenticate_key(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> UserDB:
    """
    Authenticate using basic bearer token. Used for calling
    the question-answering endpoints
    """
    token = credentials.credentials

    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        try:
            user_db = await get_user_by_token(token, asession)
            return user_db
        except UserNotFoundError as err:
            raise HTTPException(status_code=401, detail="Invalid api key") from err


async def authenticate_credentials(
    *, username: str, password: str
) -> Optional[AuthenticatedUser]:
    """
    Authenticate user using username and password.
    """
    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        try:
            user_db = await get_user_by_username(username, asession)
            if verify_password_salted_hash(password, user_db.hashed_password):
                # hardcode "fullaccess" now, but may use it in the future
                return AuthenticatedUser(username=username, access_level="fullaccess")
            else:
                return None
        except UserNotFoundError:
            return None


async def authenticate_or_create_google_user(
    *, google_email: str
) -> Optional[AuthenticatedUser]:
    """
    Check if user exists in Db. If not, create user
    """
    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        try:
            user_db = await get_user_by_username(google_email, asession)
            return AuthenticatedUser(
                username=user_db.username, access_level="fullaccess"
            )
        except UserNotFoundError:
            user = UserCreate(username=google_email)
            user_db = await save_user_to_db(user, asession)
            return AuthenticatedUser(
                username=user_db.username, access_level="fullaccess"
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
                user_db = await get_user_by_username(username, asession)
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
    expire = datetime.utcnow() + timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))

    payload["exp"] = expire
    payload["iat"] = datetime.utcnow()
    payload["sub"] = username
    payload["type"] = "access_token"

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
