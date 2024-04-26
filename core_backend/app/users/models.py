from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    String,
    # delete,
    select,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ..models import Base
from .schemas import UserCreate


class UserDB(Base):
    """
    SQL Alchemy data model for users
    """

    __tablename__ = "user"

    user_id: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)

    # retrieval_token: Mapped[str] = mapped_column(String, nullable=False)

    created_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<{self.username} mapped to #{self.user_id}>"


async def save_user_to_db(
    user: UserCreate,
    asession: AsyncSession,
) -> UserDB:
    """
    Saves a user in the database
    """

    # Check if user with same username already exists
    stmt = select(UserDB).where(UserDB.username == user.username)
    result = await asession.execute(stmt)
    try:
        result.scalar_one()
        raise ValueError(f"User with username {user.username} already exists.")
    except NoResultFound:
        pass

    content_db = UserDB(
        user_id=user.user_id,
        username=user.username,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    )

    asession.add(content_db)

    await asession.commit()
    await asession.refresh(content_db)

    return content_db


async def get_user_by_username(
    username: str,
    asession: AsyncSession,
) -> Optional[UserDB]:
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
        raise ValueError(f"User with username {username} does not exist.") from err


# async def get_user_by_token(...)
