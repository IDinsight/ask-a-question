from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    delete,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..models import Base
from .schemas import TagCreate

content_tags_table = Table(
    "content_tag",
    Base.metadata,
    Column("content_id", Integer, ForeignKey("content.content_id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tag.tag_id"), primary_key=True),
)


class TagDB(Base):
    """
    SQL Alchemy data model for tags
    """

    __tablename__ = "tag"

    tag_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )
    tag_name: Mapped[str] = mapped_column(String(length=50), nullable=False)
    created_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    contents = relationship(
        "ContentDB", secondary=content_tags_table, back_populates="content_tags"
    )

    def __repr__(self) -> str:
        """Return string representation of the TagDB object"""
        return f"TagDB(tag_id={self.tag_id}, " f"tag_name='{self.tag_name}')>"


async def save_tag_to_db(
    user_id: int,
    tag: TagCreate,
    asession: AsyncSession,
) -> TagDB:
    """
    Saves a tag in the database
    """

    tag_db = TagDB(
        tag_name=tag.tag_name,
        user_id=user_id,
        contents=[],
        created_datetime_utc=datetime.now(timezone.utc),
        updated_datetime_utc=datetime.now(timezone.utc),
    )

    asession.add(tag_db)

    await asession.commit()
    await asession.refresh(tag_db)

    return tag_db


async def update_tag_in_db(
    user_id: int,
    tag_id: int,
    tag: TagCreate,
    asession: AsyncSession,
) -> TagDB:
    """
    Updates a tag in the database
    """

    tag_db = TagDB(
        tag_id=tag_id,
        user_id=user_id,
        tag_name=tag.tag_name,
        created_datetime_utc=datetime.now(timezone.utc),
        updated_datetime_utc=datetime.now(timezone.utc),
    )

    tag_db = await asession.merge(tag_db)
    await asession.commit()
    await asession.refresh(tag_db)

    return tag_db


async def delete_tag_from_db(
    user_id: int,
    tag_id: int,
    asession: AsyncSession,
) -> None:
    """
    Deletes a tag from the database
    """
    association_stmt = delete(content_tags_table).where(
        content_tags_table.c.tag_id == tag_id
    )
    await asession.execute(association_stmt)
    stmt = delete(TagDB).where(TagDB.user_id == user_id).where(TagDB.tag_id == tag_id)
    await asession.execute(stmt)
    await asession.commit()


async def get_tag_from_db(
    user_id: int,
    tag_id: int,
    asession: AsyncSession,
) -> Optional[TagDB]:
    """
    Retrieves a tag from the database
    """
    stmt = select(TagDB).where(TagDB.user_id == user_id).where(TagDB.tag_id == tag_id)
    tag_row = (await asession.execute(stmt)).first()
    if tag_row:
        return tag_row[0]
    else:
        return None


async def get_list_of_tag_from_db(
    user_id: int, asession: AsyncSession, offset: int = 0, limit: Optional[int] = None
) -> List[TagDB]:
    """
    Retrieves all Tags from the database
    """
    stmt = select(TagDB).where(TagDB.user_id == user_id).order_by(TagDB.tag_id)
    if offset > 0:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    tag_rows = (await asession.execute(stmt)).all()

    return [c[0] for c in tag_rows] if tag_rows else []


async def validate_tags(
    user_id: int, tags: List[int], asession: AsyncSession
) -> tuple[bool, List[int] | List[TagDB]]:
    """
    Validates tags to make sure the tags exist in the database
    """
    stmt = select(TagDB).where(TagDB.user_id == user_id).where(TagDB.tag_id.in_(tags))
    tags_db = (await asession.execute(stmt)).all()
    tag_rows = [c[0] for c in tags_db] if tags_db else []
    if len(tags) != len(tag_rows):
        invalid_tags = set(tags) - set([c[0].tag_id for c in tags_db])
        return False, list(invalid_tags)

    else:
        return True, tag_rows


async def is_tag_name_unique(
    user_id: int, tag_name: str, asession: AsyncSession
) -> bool:
    """
    Check if the tag name is unique
    """
    stmt = (
        select(TagDB).where(TagDB.user_id == user_id).where(TagDB.tag_name == tag_name)
    )
    tag_row = (await asession.execute(stmt)).first()
    return not tag_row
