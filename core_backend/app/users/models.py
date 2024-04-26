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
from sqlalchemy.orm import Mapped, Session, mapped_column

from ..models import Base
from .schemas import UserCreate


class UserDB(Base):
    """
    SQL Alchemy data model for users
    """

    __tablename__ = "user"

    user_id: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)

    retrieval_token: Mapped[str] = mapped_column(String, nullable=False)

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
        retrieval_token=user.retrieval_token,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    )

    asession.add(content_db)

    await asession.commit()
    await asession.refresh(content_db)

    return content_db


# TEMPORARY - sync version of save_user_to_db for loading users on app load
def save_user_to_db_sync(
    user: UserCreate,
    session: Session,
) -> UserDB:
    """
    Saves a user in the database
    """

    # Check if user with same username already exists
    stmt = select(UserDB).where(UserDB.username == user.username)
    result = session.execute(stmt)
    try:
        result.scalar_one()
        raise ValueError(f"User with username {user.username} already exists.")
    except NoResultFound:
        pass

    content_db = UserDB(
        user_id=user.user_id,
        username=user.username,
        retrieval_token=user.retrieval_token,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    )

    session.add(content_db)

    session.commit()
    session.refresh(content_db)

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


async def get_user_by_token(
    token: str,
    asession: AsyncSession,
) -> Optional[UserDB]:
    """
    Retrieves a user by token
    """

    # Check if user with same username already exists
    stmt = select(UserDB).where(UserDB.retrieval_token == token)
    result = await asession.execute(stmt)
    try:
        user = result.scalar_one()
        return user
    except NoResultFound as err:
        # remove logging of the actual token here
        raise ValueError(f"User with token {token} does not exist.") from err
