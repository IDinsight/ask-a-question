from datetime import datetime
from typing import Dict, List

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JSONDict = Dict[str, str]


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models"""

    pass


class UserQuery(Base):
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

    feedback: Mapped[List["Feedback"]] = relationship(
        "Feedback", back_populates="query", lazy=True
    )
    responses: Mapped[List["UserQueryResponsesDB"]] = relationship(
        "UserQueryResponsesDB", back_populates="query", lazy=True
    )

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<Query #{self.query_id}> {self.query_text}>"


class UserQueryResponsesDB(Base):
    """
    SQLAlchemy data model for responses sent to user
    """

    __tablename__ = "user-query-responses"

    response_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("user-queries.query_id"))
    responses: Mapped[str] = mapped_column(
        String
    )  # Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    response_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    query: Mapped[UserQuery] = relationship(
        "UserQuery", back_populates="responses", lazy=True
    )

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<Responses for query #{self.query_id}"


class Feedback(Base):
    """
    SQLAlchemy data model for feedback provided by user
    """

    __tablename__ = "feedback"

    feedback_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("user-queries.query_id"))
    feedback_text: Mapped[str] = mapped_column(String, nullable=False)
    feedback_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    query: Mapped[UserQuery] = relationship(
        "UserQuery", back_populates="feedback", lazy=True
    )

    def __repr__(self) -> str:
        """Pretty Print"""
        return (
            f"<Feedback #{self.feedback_id} for query "
            f"#{self.query_id}> {self.feedback_text}"
        )


class Content(Base):
    """
    SQLAlchemy data model for content
    """

    __tablename__ = "content"

    content_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    content_text: Mapped[str] = mapped_column(String, nullable=False)
    content_metadata: Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    created_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<Content #{self.content_id}> {self.content_text}>"
