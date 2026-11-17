"""SQLAlchemy ORM models for the `urgency_detection` feature."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.sql.sqltypes import ARRAY

from app.core.database import Base, JSONDict


class UrgencyQueryDB(Base):
    """ORM for managing urgency detection queries.

    This database ties into the Admin app and allows the user to view, add, edit,
    and delete content in the `urgency_query` table.
    """

    __tablename__ = "urgency_query"

    feedback_secret_key: Mapped[str] = mapped_column(String, nullable=False)
    message_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    message_text: Mapped[str] = mapped_column(String, nullable=False)
    response: Mapped["UrgencyResponseDB"] = relationship(
        "UrgencyResponseDB", back_populates="query", uselist=False, lazy=True
    )
    urgency_query_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Construct the string representation of the `UrgencyQueryDB` object.

        Returns
        -------
        str
            A string representation of the `UrgencyQueryDB` object.
        """

        return (
            f"Urgency Query {self.urgency_query_id} for workspace ID "
            f"{self.workspace_id}\nmessage_text={self.message_text}"
        )


class UrgencyResponseDB(Base):
    """ORM for managing urgency responses.

    This database ties into the Admin app and allows the user to view, add, edit,
    and delete content in the `urgency_response` table.
    """

    __tablename__ = "urgency_response"

    details: Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    is_urgent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    matched_rules: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    query: Mapped[UrgencyQueryDB] = relationship(
        "UrgencyQueryDB", back_populates="response", lazy=True
    )
    query_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("urgency_query.urgency_query_id", ondelete="CASCADE")
    )
    response_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    urgency_response_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Construct the string representation of the `UrgencyResponseDB` object.

        Returns
        -------
        str
            A string representation of the `UrgencyResponseDB` object.
        """

        return (
            f"Urgency Response {self.urgency_response_id} for query #{self.query_id} "
            f"is_urgent={self.is_urgent}"
        )
