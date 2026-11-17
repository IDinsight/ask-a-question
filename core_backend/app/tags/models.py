"""SQLAlchemy ORM models for the `tags` feature."""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

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
