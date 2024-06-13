from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    select,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ..models import Base
from ..utils import get_key_hash, get_password_salted_hash, get_random_string
from .schemas import UserCreate, UserCreateWithPassword

PASSWORD_LENGTH = 12


class UserNotFoundError(Exception):
    """Exception raised when a user is not found in the database."""


class UserAlreadyExistsError(Exception):
    """Exception raised when a user already exists in the database."""


class UserDB(Base):
    """
    SQL Alchemy data model for users
    """

    __tablename__ = "user"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(96), nullable=False)

    hashed_api_key: Mapped[str] = mapped_column(String(96), nullable=True, unique=True)

    created_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<{self.username} mapped to #{self.user_id}>"


async def save_user_to_db(
    user: UserCreateWithPassword | UserCreate,
    asession: AsyncSession,
) -> UserDB:
    """
    Saves a user in the database
    """

    # Check if user with same username already exists
    stmt = select(UserDB).where(UserDB.username == user.username)
    result = await asession.execute(stmt)
    try:
        result.one()
        raise UserAlreadyExistsError(
            f"User with username {user.username} already exists."
        )
    except NoResultFound:
        pass

    if isinstance(user, UserCreateWithPassword):
        hashed_password = get_password_salted_hash(user.password)
    else:
        random_password = get_random_string(PASSWORD_LENGTH)
        hashed_password = get_password_salted_hash(random_password)

    user_db = UserDB(
        username=user.username,
        hashed_password=hashed_password,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    )

    asession.add(user_db)
    await asession.commit()
    await asession.refresh(user_db)

    return user_db


async def update_user_api_key(
    user_db: UserDB,
    new_api_key: str,
    asession: AsyncSession,
) -> UserDB:
    """
    Updates a user's API key
    """

    user_db.hashed_api_key = get_key_hash(new_api_key)
    user_db.updated_datetime_utc = datetime.utcnow()

    await asession.commit()
    await asession.refresh(user_db)

    return user_db


async def get_user_by_username(
    username: str,
    asession: AsyncSession,
) -> UserDB:
    """
    Retrieves a user by username
    """

    # Check if user with same username already exists
    stmt = select(UserDB).where(UserDB.username == username)
    result = await asession.execute(stmt)
    try:
        user = result.scalar_one()
        return user
    except NoResultFound as err:
        raise UserNotFoundError(
            f"User with username {username} does not exist."
        ) from err


async def get_user_by_token(
    token: str,
    asession: AsyncSession,
) -> UserDB:
    """
    Retrieves a user by token
    """

    hashed_token = get_key_hash(token)

    stmt = select(UserDB).where(UserDB.hashed_api_key == hashed_token)
    result = await asession.execute(stmt)
    try:
        user = result.scalar_one()
        return user
    except NoResultFound as err:
        raise UserNotFoundError("User with given token does not exist.") from err
