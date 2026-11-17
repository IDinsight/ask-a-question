"""SQLAlchemy ORM models for the `urgency_rules` feature."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import PGVECTOR_VECTOR_SIZE
from app.core.database import Base, JSONDict


class UrgencyRuleDB(Base):
    """ORM for managing urgency detection rules.

    This database ties into the Admin app and allows the user to view, add, edit,
    and delete content in the `urgency_rule` table.
    """

    __tablename__ = "urgency_rule"

    created_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    urgency_rule_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False
    )
    urgency_rule_metadata: Mapped[JSONDict] = mapped_column(JSON, nullable=True)
    urgency_rule_text: Mapped[str] = mapped_column(String, nullable=False)
    urgency_rule_vector: Mapped[Vector] = mapped_column(
        Vector(int(PGVECTOR_VECTOR_SIZE)), nullable=False
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Construct the string representation of the `UrgencyRuleDB` object.

        Returns
        -------
        str
            A string representation of the `UrgencyRuleDB` object.
        """

        return f"<UrgencyRuleDB #{self.urgency_rule_id}: {self.urgency_rule_text})>"
