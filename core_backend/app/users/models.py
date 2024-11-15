from datetime import datetime, timezone
from typing import Sequence

import sqlalchemy as sa
from sqlalchemy import (
    ARRAY,
    Boolean,
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
from .schemas import UserCreate, UserCreateWithPassword, UserResetPassword

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
    api_key_first_characters: Mapped[str] = mapped_column(String(5), nullable=True)
    api_key_updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recovery_codes: Mapped[list] = mapped_column(ARRAY(String), nullable=True)
    content_quota: Mapped[int] = mapped_column(Integer, nullable=True)
    api_daily_quota: Mapped[int] = mapped_column(Integer, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<{self.username} mapped to #{self.user_id}>"


async def save_user_to_db(
    user: UserCreateWithPassword | UserCreate,
    asession: AsyncSession,
    recovery_codes: list[str] | None = None,
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
        content_quota=user.content_quota,
        api_daily_quota=user.api_daily_quota,
        is_admin=user.is_admin,
        hashed_password=hashed_password,
        recovery_codes=recovery_codes,
        created_datetime_utc=datetime.now(timezone.utc),
        updated_datetime_utc=datetime.now(timezone.utc),
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
    user_db.api_key_first_characters = new_api_key[:5]
    user_db.api_key_updated_datetime_utc = datetime.now(timezone.utc)
    user_db.updated_datetime_utc = datetime.now(timezone.utc)

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
    stmt = select(UserDB).where(UserDB.username == username)
    result = await asession.execute(stmt)
    try:
        user = result.scalar_one()
        return user
    except NoResultFound as err:
        raise UserNotFoundError(
            f"User with username {username} does not exist."
        ) from err


async def get_user_by_id(
    user_id: int,
    asession: AsyncSession,
) -> UserDB:
    """
    Retrieves a user by user_id
    """
    stmt = select(UserDB).where(UserDB.user_id == user_id)
    result = await asession.execute(stmt)
    try:
        user = result.scalar_one()
        return user
    except NoResultFound as err:
        raise UserNotFoundError(f"User with user_id {user_id} does not exist.") from err


async def get_content_quota_by_userid(
    user_id: int,
    asession: AsyncSession,
) -> int:
    """
    Retrieves a user's content quota by user_id
    """
    stmt = select(UserDB).where(UserDB.user_id == user_id)
    result = await asession.execute(stmt)
    try:
        content_quota = result.scalar_one().content_quota
        return content_quota
    except NoResultFound as err:
        raise UserNotFoundError(f"User with user_id {user_id} does not exist.") from err


async def get_user_by_api_key(
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


async def get_all_users(
    asession: AsyncSession,
) -> Sequence[UserDB]:
    """
    Retrieves all users
    """

    stmt = select(UserDB)
    result = await asession.execute(stmt)
    users = result.scalars().all()
    return users


async def update_user_in_db(
    user_id: int,
    user: UserCreate,
    asession: AsyncSession,
) -> UserDB:
    """
    Updates a user in the database.
    """
    user_db = UserDB(
        user_id=user_id,
        username=user.username,
        is_admin=user.is_admin,
        content_quota=user.content_quota,
        api_daily_quota=user.api_daily_quota,
        updated_datetime_utc=datetime.now(timezone.utc),
    )
    user_db = await asession.merge(user_db)

    await asession.commit()
    await asession.refresh(user_db)

    return user_db


async def is_username_valid(
    username: str,
    asession: AsyncSession,
) -> bool:
    """
    Checks if a username is valid. A new username is valid if it doesn't already exist
    in the database.
    """
    stmt = select(UserDB).where(UserDB.username == username)
    result = await asession.execute(stmt)
    try:
        result.one()
        return False
    except NoResultFound:
        return True


async def get_number_of_admin_users(asession: AsyncSession) -> int:
    """
    Retrieves the number of admin users in the database
    """
    stmt = select(UserDB).where(UserDB.is_admin == sa.true())
    result = await asession.execute(stmt)
    users = result.scalars().all()
    return len(users)


async def reset_user_password_in_db(
    user_id: int,
    user: UserResetPassword,
    asession: AsyncSession,
    recovery_codes: list[str] | None = None,
) -> UserDB:
    """
    Saves a user in the database
    """

    hashed_password = get_password_salted_hash(user.password)
    user_db = UserDB(
        user_id=user_id,
        hashed_password=hashed_password,
        recovery_codes=recovery_codes,
        updated_datetime_utc=datetime.now(timezone.utc),
    )
    user_db = await asession.merge(user_db)
    await asession.commit()
    await asession.refresh(user_db)

    return user_db
