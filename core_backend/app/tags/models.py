"""This module contains the ORM for managing content tags in the `TagDB` database."""

from datetime import datetime, timezone
from typing import Optional

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
    Column(
        "content_id",
        Integer,
        ForeignKey("content.content_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        Integer,
        ForeignKey("tag.tag_id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class TagDB(Base):
    """ORM for managing content tags."""

    __tablename__ = "tag"

    contents = relationship(
        "ContentDB", secondary=content_tags_table, back_populates="content_tags"
    )
    created_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    tag_name: Mapped[str] = mapped_column(String(length=50), nullable=False)
    updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Define the string representation for the `TagDB` class.

        Returns
        -------
        str
            A string representation of the `TagDB` class.
        """

        return f"TagDB(tag_id={self.tag_id}, " f"tag_name='{self.tag_name}')>"


async def save_tag_to_db(
    *, asession: AsyncSession, tag: TagCreate, workspace_id: int
) -> TagDB:
    """Save a tag in the `TagDB` database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    tag
        The tag to be saved.
    workspace_id
        The ID of the workspace that the tag belongs to.

    Returns
    -------
    TagDB
        The saved tag object.
    """

    tag_db = TagDB(
        contents=[],
        created_datetime_utc=datetime.now(timezone.utc),
        tag_name=tag.tag_name,
        updated_datetime_utc=datetime.now(timezone.utc),
        workspace_id=workspace_id,
    )

    asession.add(tag_db)

    await asession.commit()
    await asession.refresh(tag_db)

    return tag_db


async def update_tag_in_db(
    *, asession: AsyncSession, tag: TagCreate, tag_id: int, workspace_id: int
) -> TagDB:
    """Update a tag in the database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    tag
        The tag to be updated.
    tag_id
        The ID of the tag to update.
    workspace_id
        The ID of the workspace that the tag belongs to.

    Returns
    -------
    TagDB
        The updated tag object.
    """

    tag_db = TagDB(
        tag_id=tag_id,
        tag_name=tag.tag_name,
        updated_datetime_utc=datetime.now(timezone.utc),
        workspace_id=workspace_id,
    )

    tag_db = await asession.merge(tag_db)
    await asession.commit()
    await asession.refresh(tag_db)

    return tag_db


async def delete_tag_from_db(
    *, asession: AsyncSession, tag_id: int, workspace_id: int
) -> None:
    """Delete a tag from the database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    tag_id
        The ID of the tag to delete.
    workspace_id
        The ID of the workspace that the tag belongs to.
    """

    association_stmt = delete(content_tags_table).where(
        content_tags_table.c.tag_id == tag_id
    )
    await asession.execute(association_stmt)
    stmt = (
        delete(TagDB)
        .where(TagDB.workspace_id == workspace_id)
        .where(TagDB.tag_id == tag_id)
    )
    await asession.execute(stmt)
    await asession.commit()


async def get_tag_from_db(
    *, asession: AsyncSession, tag_id: int, workspace_id: int
) -> Optional[TagDB]:
    """Retrieve a tag from the database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    tag_id
        The ID of the tag to retrieve.
    workspace_id
        The ID of the workspace that the tag belongs to.

    Returns
    -------
    Optional[TagDB]
        The tag object if it exists, otherwise None.
    """

    stmt = (
        select(TagDB)
        .where(TagDB.workspace_id == workspace_id)
        .where(TagDB.tag_id == tag_id)
    )
    tag_row = (await asession.execute(stmt)).first()
    return tag_row[0] if tag_row else None


async def get_list_of_tag_from_db(
    *,
    asession: AsyncSession,
    limit: Optional[int] = None,
    offset: int = 0,
    workspace_id: int,
) -> list[TagDB]:
    """Retrieve all Tags from the database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    limit
        The maximum number of records to retrieve.
    offset
        The number of records to skip.
    workspace_id
        The ID of the workspace to retrieve tags from.

    Returns
    -------
    list[TagDB]
        The list of tags in the workspace.
    """

    stmt = (
        select(TagDB).where(TagDB.workspace_id == workspace_id).order_by(TagDB.tag_id)
    )
    if offset > 0:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    tag_rows = (await asession.execute(stmt)).all()

    return [c[0] for c in tag_rows] if tag_rows else []


async def validate_tags(
    *, asession: AsyncSession, tags: list[int], workspace_id: int
) -> tuple[bool, list[int] | list[TagDB]]:
    """Validates tags to make sure the tags exist in the database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    tags
        A list of tag IDs to validate.
    workspace_id
        The ID of the workspace that the tags are being created in.

    Returns
    -------
    tuple[bool, list[int] | list[TagDB]]
        A tuple containing a boolean value indicating whether the tags are valid and a
        list of tag IDs or a list of `TagDB` objects.
    """

    stmt = (
        select(TagDB)
        .where(TagDB.workspace_id == workspace_id)
        .where(TagDB.tag_id.in_(tags))
    )
    tags_db = (await asession.execute(stmt)).all()
    tag_rows = [c[0] for c in tags_db] if tags_db else []
    if len(tags) != len(tag_rows):
        invalid_tags = set(tags) - set(  # pylint: disable=R1718
            [c[0].tag_id for c in tags_db]
        )
        return False, list(invalid_tags)
    return True, tag_rows


async def is_tag_name_unique(
    *, asession: AsyncSession, tag_name: str, workspace_id: int
) -> bool:
    """Check if the tag name is unique.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    tag_name
        The name of the tag to check.
    workspace_id
        The ID of the workspace that the tag belongs to.

    Returns
    -------
    bool
        Specifies whether the tag name is unique.
    """

    stmt = (
        select(TagDB)
        .where(TagDB.workspace_id == workspace_id)
        .where(TagDB.tag_name == tag_name)
    )
    tag_row = (await asession.execute(stmt)).first()
    return not tag_row
