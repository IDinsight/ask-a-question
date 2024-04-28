from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.schema import ForeignKey

from ..models import Base, JSONDict
from .schemas import UrgencyQuery, UrgencyResponse


class UrgencyQueryDB(Base):
    """
    Urgency query database model.
    """

    __tablename__ = "urgency-queries"

    urgency_query_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    message_text: Mapped[str] = mapped_column(String, nullable=False)
    message_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    feedback_secret_key: Mapped[str] = mapped_column(String, nullable=False)

    response: Mapped["UrgencyResponseDB"] = relationship(
        "UrgencyResponseDB", back_populates="query", uselist=False, lazy=True
    )


async def save_urgency_query_to_db(
    feedback_secret_key: str, urgency_query: UrgencyQuery, asession: AsyncSession
) -> UrgencyQueryDB:
    """
    Saves a user query to the database.
    """
    urgency_query_db = UrgencyQueryDB(
        feedback_secret_key=feedback_secret_key,
        message_datetime_utc=datetime.utcnow(),
        **urgency_query.model_dump(),
    )
    asession.add(urgency_query_db)
    await asession.commit()
    await asession.refresh(urgency_query_db)
    return urgency_query_db


async def check_secret_key_match(
    secret_key: str, query_id: int, asession: AsyncSession
) -> bool:
    """
    Check if the secret key matches the one generated for query id
    """
    stmt = select(UrgencyQueryDB.feedback_secret_key).where(
        UrgencyQueryDB.urgency_query_id == query_id
    )
    query_record = (await asession.execute(stmt)).first()

    if (query_record is not None) and (query_record[0] == secret_key):
        return True
    else:
        return False


class UrgencyResponseDB(Base):
    """
    Urgency response database model.
    """

    __tablename__ = "urgency-responses"

    urgency_response_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    is_urgent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    details: Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    query_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("urgency-queries.urgency_query_id")
    )
    response_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    query: Mapped[UrgencyQueryDB] = relationship(
        "UrgencyQueryDB", back_populates="response", lazy=True
    )

    def __repr__(self) -> str:
        """Pretty print the response."""
        return (
            f"Urgency Response {self.urgency_response_id} for query #{self.query_id} "
            f"is_urgent={self.is_urgent}"
        )


async def save_urgency_response_to_db(
    urgency_query_db: UrgencyQueryDB,
    response: UrgencyResponse,
    asession: AsyncSession,
) -> UrgencyResponseDB:
    """
    Saves the user query response to the database.
    """
    urgency_query_responses_db = UrgencyResponseDB(
        query_id=urgency_query_db.urgency_query_id,
        is_urgent=response.is_urgent,
        details=response.model_dump()["details"],
        response_datetime_utc=datetime.utcnow(),
    )
    asession.add(urgency_query_responses_db)
    await asession.commit()
    await asession.refresh(urgency_query_responses_db)
    return urgency_query_responses_db
