"""SQLAlchemy ORM models for the `contents` feature."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    column,
    false,
    true,
)
from sqlalchemy.dialects.postgresql import ARRAY  # or JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import case

from app.core.config import (
    PGVECTOR_DISTANCE,
    PGVECTOR_EF_CONSTRUCTION,
    PGVECTOR_M,
    PGVECTOR_VECTOR_SIZE,
)
from app.core.database import Base, JSONDict
from app.tags.models import content_tags_table


class ContentDB(Base):
    """ORM for managing content.

    This database ties into the Admin app and allows the user to view, add, edit,
    and delete content in the `content` table.
    """

    __tablename__ = "content"
    __table_args__ = (
        Index(
            "ix_content_embedding",
            "content_embedding",
            postgresql_using="hnsw",
            postgresql_with={
                "M": {PGVECTOR_M},
                "ef_construction": {PGVECTOR_EF_CONSTRUCTION},
            },
            postgresql_ops={"embedding": {PGVECTOR_DISTANCE}},
        ),
    )

    content_embedding: Mapped[Vector] = mapped_column(
        Vector(int(PGVECTOR_VECTOR_SIZE)), nullable=False
    )
    content_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    content_metadata: Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    content_tags = relationship(
        "TagDB", secondary=content_tags_table, back_populates="contents"
    )
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_title: Mapped[str] = mapped_column(Text, nullable=False)
    created_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    display_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        Computed(
            case(
                (column("is_archived") == true(), false()),
                (column("is_validated") == false(), false()),
                else_=true(),
            )
        ),
    )
    is_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    positive_votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negative_votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    query_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    related_contents_id: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, default=list
    )
    updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Construct the string representation of the `ContentDB` object.

        Returns
        -------
        str
            A string representation of the `ContentDB` object.
        """

        return (
            f"ContentDB(content_id={self.content_id}, "
            f"content_embedding=..., "
            f"content_title={self.content_title}, "
            f"content_text={self.content_text}, "
            f"content_metadata={self.content_metadata}, "
            f"content_tags={self.content_tags}, "
            f"created_datetime_utc={self.created_datetime_utc}, "
            f"display_number={self.display_number}, "
            f"is_archived={self.is_archived}, "
            f"is_validated={self.is_validated}, "
            f"is_active={self.is_active}, "
            f"updated_datetime_utc={self.updated_datetime_utc}, "
            f"workspace_id={self.workspace_id}"
        )
