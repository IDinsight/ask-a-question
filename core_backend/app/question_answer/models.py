from datetime import datetime
from typing import List

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..models import Base, JSONDict
from .schemas import (
    ResponseFeedbackBase,
    UserQueryBase,
    UserQueryResponse,
    UserQueryResponseError,
)


class UserQueryDB(Base):
    """
    SQLAlchemy data model for questions asked by user
    """

    __tablename__ = "user-queries"

    query_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    feedback_secret_key: Mapped[str] = mapped_column(String, nullable=False)
    query_text: Mapped[str] = mapped_column(String, nullable=False)
    query_metadata: Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    query_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    feedback: Mapped[List["ResponseFeedbackDB"]] = relationship(
        "ResponseFeedbackDB", back_populates="query", lazy=True
    )
    response: Mapped[List["UserQueryResponseDB"]] = relationship(
        "UserQueryResponseDB", back_populates="query", lazy=True
    )
    response_error: Mapped[List["UserQueryResponseErrorDB"]] = relationship(
        "UserQueryResponseErrorDB", back_populates="query", lazy=True
    )

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<Query #{self.query_id}> {self.query_text}>"


async def save_user_query_to_db(
    feedback_secret_key: str, user_query: UserQueryBase, asession: AsyncSession
) -> UserQueryDB:
    """
    Saves a user query to the database.
    """
    user_query_db = UserQueryDB(
        feedback_secret_key=feedback_secret_key,
        query_datetime_utc=datetime.utcnow(),
        **user_query.model_dump(),
    )
    asession.add(user_query_db)
    await asession.commit()
    await asession.refresh(user_query_db)
    return user_query_db


async def check_secret_key_match(
    secret_key: str, query_id: int, asession: AsyncSession
) -> bool:
    """
    Check if the secret key matches the one generated for query id
    """
    stmt = select(UserQueryDB.feedback_secret_key).where(
        UserQueryDB.query_id == query_id
    )
    query_record = (await asession.execute(stmt)).first()

    if (query_record is not None) and (query_record[0] == secret_key):
        return True
    else:
        return False


class UserQueryResponseDB(Base):
    """
    SQLAlchemy data model for responses sent to user
    """

    __tablename__ = "user-query-responses"

    response_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("user-queries.query_id"))
    content_response: Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    llm_response: Mapped[str] = mapped_column(String, nullable=True)
    response_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    query: Mapped[UserQueryDB] = relationship(
        "UserQueryDB", back_populates="response", lazy=True
    )

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<Responses for query #{self.query_id}"


async def save_query_response_to_db(
    user_query_db: UserQueryDB,
    response: UserQueryResponse,
    asession: AsyncSession,
) -> UserQueryResponseDB:
    """
    Saves the user query response to the database.
    """
    user_query_responses_db = UserQueryResponseDB(
        query_id=user_query_db.query_id,
        content_response=response.model_dump()["content_response"],
        llm_response=response.model_dump()["llm_response"],
        response_datetime_utc=datetime.utcnow(),
    )
    asession.add(user_query_responses_db)
    await asession.commit()
    await asession.refresh(user_query_responses_db)
    return user_query_responses_db


class UserQueryResponseErrorDB(Base):
    """
    SQLAlchemy data model for errors sent to user
    """

    __tablename__ = "user-query-response-errors"

    error_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("user-queries.query_id"))
    error_message: Mapped[str] = mapped_column(String, nullable=False)
    error_type: Mapped[str] = mapped_column(String, nullable=False)
    error_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    debug_info: Mapped[JSONDict] = mapped_column(JSON, nullable=False)

    query: Mapped[UserQueryDB] = relationship(
        "UserQueryDB", back_populates="response_error", lazy=True
    )

    def __repr__(self) -> str:
        """Pretty Print"""
        return (
            f"<Error for query #{self.query_id}: "
            f"{self.error_type} | {self.error_message}>"
        )


async def save_query_response_error_to_db(
    user_query_db: UserQueryDB,
    error: UserQueryResponseError,
    asession: AsyncSession,
) -> UserQueryResponseErrorDB:
    """
    Saves the user query response error to the database.
    """
    user_query_response_error_db = UserQueryResponseErrorDB(
        query_id=user_query_db.query_id,
        error_message=error.error_message,
        error_type=error.error_type,
        error_datetime_utc=datetime.utcnow(),
        debug_info=error.debug_info,
    )
    asession.add(user_query_response_error_db)
    await asession.commit()
    await asession.refresh(user_query_response_error_db)
    return user_query_response_error_db


class ResponseFeedbackDB(Base):
    """
    SQLAlchemy data model for feedback provided by user
    """

    __tablename__ = "feedback"

    feedback_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    feedback_sentiment: Mapped[str] = mapped_column(String, nullable=True)
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("user-queries.query_id"))
    feedback_text: Mapped[str] = mapped_column(String, nullable=True)
    feedback_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    query: Mapped[UserQueryDB] = relationship(
        "UserQueryDB", back_populates="feedback", lazy=True
    )

    def __repr__(self) -> str:
        """Pretty Print"""
        return (
            f"<Feedback #{self.feedback_id} for query "
            f"#{self.query_id}> {self.feedback_text}"
        )


async def save_response_feedback_to_db(
    feedback: ResponseFeedbackBase,
    asession: AsyncSession,
) -> ResponseFeedbackDB:
    """
    Saves feedback to the database.
    """
    feedback_db = ResponseFeedbackDB(
        feedback_datetime_utc=datetime.utcnow(),
        feedback_sentiment=feedback.feedback_sentiment,
        query_id=feedback.query_id,
        feedback_text=feedback.feedback_text,
    )
    asession.add(feedback_db)
    await asession.commit()
    await asession.refresh(feedback_db)
    return feedback_db
