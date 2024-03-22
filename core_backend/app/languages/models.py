from datetime import datetime
from datetime import timezone as tz
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    delete,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Index

from ..models import Base
from .schemas import LanguageBase


class LanguageDB(Base):
    """
    SQL Alchemy data model for language
    """

    __tablename__ = "languages"

    language_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    language_name: Mapped[str] = mapped_column(String, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index(
            "ix_languages_is_default_true",
            "is_default",
            unique=True,
            postgresql_where=(is_default.is_(True)),
        ),
    )

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<Language #{self.language_id}:  {self.language_name}>"


async def save_language_to_db(
    language: LanguageBase,
    asession: AsyncSession,
) -> LanguageDB:
    """
    Saves a new language in the database
    """

    language_db = LanguageDB(
        language_name=language.language_name,
        is_default=language.is_default,
        created_datetime_utc=datetime.now(tz.utc).replace(tzinfo=None),
        updated_datetime_utc=datetime.now(tz.utc).replace(tzinfo=None),
    )
    asession.add(language_db)

    await asession.commit()
    await asession.refresh(language_db)

    return language_db


async def update_language_in_db(
    language_id: int,
    language: LanguageBase,
    asession: AsyncSession,
) -> LanguageDB:
    """
    Updates a language in the database
    """

    language_db = LanguageDB(
        language_id=language_id,
        is_default=language.is_default,
        language_name=language.language_name,
        updated_datetime_utc=datetime.now(tz.utc).replace(tzinfo=None),
    )

    language_db = await asession.merge(language_db)
    await asession.commit()
    return language_db


async def delete_language_from_db(
    language_id: int,
    asession: AsyncSession,
) -> None:
    """
    Deletes a content from the database
    """
    stmt = delete(LanguageDB).where(LanguageDB.language_id == language_id)
    await asession.execute(stmt)
    await asession.commit()


async def get_language_from_db(
    language_id: int,
    asession: AsyncSession,
) -> Optional[LanguageDB]:
    """
    Retrieves a content from the database
    """
    stmt = select(LanguageDB).where(LanguageDB.language_id == language_id)
    language_row = (await asession.execute(stmt)).scalar_one_or_none()
    return language_row


async def get_default_language_from_db(
    asession: AsyncSession,
) -> Optional[LanguageDB]:
    """
    Retrieves a content from the database
    """
    truth_bool = True
    stmt = select(LanguageDB).where(LanguageDB.is_default == truth_bool)
    language_row = (await asession.execute(stmt)).scalar_one_or_none()
    return language_row


async def get_list_of_languages_from_db(
    asession: AsyncSession, offset: int = 0, limit: Optional[int] = None
) -> List[LanguageDB]:
    """
    Retrieves all content from the database
    """
    stmt = select(LanguageDB)
    if offset > 0:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    language_rows = (await asession.execute(stmt)).all()

    return [c[0] for c in language_rows] if language_rows else []


async def is_language_name_unique(language_name: str, asession: AsyncSession) -> bool:
    """
    Check if the language name is unique
    """
    stmt = select(LanguageDB).where(LanguageDB.language_name == language_name)
    language_row = (await asession.execute(stmt)).scalar_one_or_none()
    if language_row:
        return False
    else:
        return True
