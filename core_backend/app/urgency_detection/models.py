"""This module contains the ORM for managing urgency detection queries in the
`UrgencyQueryDB` database and functions for interacting with the database.
"""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.sql.sqltypes import ARRAY

from ..models import Base, JSONDict
from .schemas import UrgencyQuery, UrgencyResponse


class UrgencyQueryDB(Base):
    """ORM for managing urgency detection queries.

    This database ties into the Admin app and allows the user to view, add, edit,
    and delete content in the `urgency_query` table.
    """

    __tablename__ = "urgency_query"

    urgency_query_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )
    message_text: Mapped[str] = mapped_column(String, nullable=False)
    message_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    feedback_secret_key: Mapped[str] = mapped_column(String, nullable=False)

    response: Mapped["UrgencyResponseDB"] = relationship(
        "UrgencyResponseDB", back_populates="query", uselist=False, lazy=True
    )

    def __repr__(self) -> str:
        """Construct the string representation of the `UrgencyQueryDB` object.

        Returns
        -------
        str
            A string representation of the `UrgencyQueryDB` object.
        """

        return (
            f"Urgency Query {self.urgency_query_id} for user #{self.user_id}\n"
            f"message_text={self.message_text}"
        )


async def save_urgency_query_to_db(
    user_id: int,
    feedback_secret_key: str,
    urgency_query: UrgencyQuery,
    asession: AsyncSession,
) -> UrgencyQueryDB:
    """Saves a user query to the database.

    Parameters
    ----------
    user_id
        The ID of the user requesting to save the urgency query to the database.
    feedback_secret_key
        The secret key for the feedback.
    urgency_query
        The urgency query to save to the database.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    UrgencyQueryDB
        The urgency query object that was saved to the database.
    """

    urgency_query_db = UrgencyQueryDB(
        user_id=user_id,
        feedback_secret_key=feedback_secret_key,
        message_datetime_utc=datetime.now(timezone.utc),
        **urgency_query.model_dump(),
    )
    asession.add(urgency_query_db)
    await asession.commit()
    await asession.refresh(urgency_query_db)
    return urgency_query_db


async def check_secret_key_match(
    secret_key: str, query_id: int, asession: AsyncSession
) -> bool:
    """Check if the secret key matches the one generated for the query ID.

    Parameters
    ----------
    secret_key
        The key to check.
    query_id
        The ID of the query to check.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    bool
        `True` if the secret key matches the one generated for the query ID, `False`
        otherwise.
    """

    stmt = select(UrgencyQueryDB.feedback_secret_key).where(
        UrgencyQueryDB.urgency_query_id == query_id
    )
    query_record = (await asession.execute(stmt)).first()
    return (query_record is not None) and (query_record[0] == secret_key)


class UrgencyResponseDB(Base):
    """ORM for managing urgency responses.

    This database ties into the Admin app and allows the user to view, add, edit,
    and delete content in the `urgency_response` table.
    """

    __tablename__ = "urgency_response"

    urgency_response_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    is_urgent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    matched_rules: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True)
    details: Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    query_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("urgency_query.urgency_query_id")
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )
    response_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    query: Mapped[UrgencyQueryDB] = relationship(
        "UrgencyQueryDB", back_populates="response", lazy=True
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


async def save_urgency_response_to_db(
    urgency_query_db: UrgencyQueryDB,
    response: UrgencyResponse,
    asession: AsyncSession,
) -> UrgencyResponseDB:
    """Saves the user query response to the database.

    Parameters
    ----------
    urgency_query_db
        The urgency query database object.
    response
        The urgency response object to save to the database.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    UrgencyResponseDB
        The urgency response object that was saved to the database.
    """

    urgency_query_responses_db = UrgencyResponseDB(
        query_id=urgency_query_db.urgency_query_id,
        user_id=urgency_query_db.user_id,
        is_urgent=response.is_urgent,
        details=response.model_dump()["details"],
        matched_rules=response.matched_rules,
        response_datetime_utc=datetime.now(timezone.utc),
    )
    asession.add(urgency_query_responses_db)
    await asession.commit()
    await asession.refresh(urgency_query_responses_db)
    return urgency_query_responses_db
