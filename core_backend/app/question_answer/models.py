"""SQLAlchemy ORM models for the `question_answer` feature."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.contents.models import ContentDB
from app.core.database import Base, JSONDict


class QueryDB(Base):
    """ORM for managing questions asked by the user.

    This database ties into the Admin app and stores various fields associated with a
    user's query.
    """

    __tablename__ = "query"

    content_feedback: Mapped[list["ContentFeedbackDB"]] = relationship(
        "ContentFeedbackDB", back_populates="query", lazy="select"
    )
    feedback_secret_key: Mapped[str] = mapped_column(String, nullable=False)
    generate_tts: Mapped[bool] = mapped_column(Boolean, nullable=True)
    query_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    query_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    query_generate_llm_response: Mapped[bool] = mapped_column(Boolean, nullable=False)
    query_metadata: Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    query_text: Mapped[str] = mapped_column(String, nullable=False)
    response: Mapped[list["QueryResponseDB"]] = relationship(
        "QueryResponseDB", back_populates="query", lazy="select"
    )
    response_feedback: Mapped[list["ResponseFeedbackDB"]] = relationship(
        "ResponseFeedbackDB", back_populates="query", lazy="select"
    )
    session_id: Mapped[int] = mapped_column(Integer, nullable=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Construct the string representation of the `QueryDB` object.

        Returns
        -------
        str
            A string representation of the `QueryDB` object.
        """

        return (
            f"<Query #{self.query_id}>, "
            f"LLM response requested: {self.query_generate_llm_response}, "
            f"Query text: {self.query_text}>"
        )


class QueryResponseDB(Base):
    """ORM for managing query responses sent to the user.

    This database ties into the Admin app and stores various fields associated with
    responses to a user's query.
    """

    __tablename__ = "query_response"

    debug_info: Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    error_message: Mapped[str] = mapped_column(String, nullable=True)
    error_type: Mapped[str] = mapped_column(String, nullable=True)
    is_error: Mapped[bool] = mapped_column(Boolean, nullable=False)
    query: Mapped[QueryDB] = relationship(
        "QueryDB", back_populates="response", lazy="select"
    )
    query_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("query.query_id", ondelete="CASCADE")
    )
    llm_response: Mapped[str] = mapped_column(String, nullable=True)
    response_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    response_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    search_results: Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    session_id: Mapped[int] = mapped_column(Integer, nullable=True)
    tts_filepath: Mapped[str] = mapped_column(String, nullable=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Construct the string representation of the `QueryResponseDB` object.

        Returns
        -------
        str
            A string representation of the `QueryResponseDB` object.
        """

        return f"<Responses for query #{self.query_id}"


class QueryResponseContentDB(Base):
    """ORM for storing what content was returned for a given query. Allows us to track
    how many times a given content was returned in a time period.
    """

    __tablename__ = "query_response_content"
    __table_args__ = (
        Index(
            "ix_workspace_id_created_datetime", "workspace_id", "created_datetime_utc"
        ),
    )

    content_for_query_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False
    )
    content_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("content.content_id", ondelete="CASCADE"), nullable=False
    )
    created_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    query_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("query.query_id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[int] = mapped_column(Integer, nullable=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Construct the string representation of the `QueryResponseContentDB` object.

        Returns
        -------
        str
            A string representation of the `QueryResponseContentDB` object.
        """

        return (
            f"ContentForQueryDB(content_for_query_id={self.content_for_query_id}, "
            f"workspace_id={self.workspace_id}, "
            f"session_id={self.session_id}, "
            f"content_id={self.content_id}, "
            f"query_id={self.query_id}, "
            f"created_datetime_utc={self.created_datetime_utc})"
        )


class ResponseFeedbackDB(Base):
    """ORM for managing feedback provided by user for AI responses to queries.

    This database ties into the Admin app and stores various fields associated with AI
    feedback response to a user's query.
    """

    __tablename__ = "query_response_feedback"

    feedback_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    feedback_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    feedback_sentiment: Mapped[str] = mapped_column(String, nullable=True)
    feedback_text: Mapped[str] = mapped_column(String, nullable=True)
    query: Mapped[QueryDB] = relationship(
        "QueryDB", back_populates="response_feedback", lazy="select"
    )
    query_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("query.query_id", ondelete="CASCADE")
    )
    session_id: Mapped[int] = mapped_column(Integer, nullable=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Construct the string representation of the `ResponseFeedbackDB` object.

        Returns
        -------
        str
            A string representation of the `ResponseFeedbackDB` object.
        """

        return (
            f"<Feedback #{self.feedback_id} for query "
            f"#{self.query_id}> {self.feedback_text}"
        )


class ContentFeedbackDB(Base):
    """ORM for managing feedback provided by user for content responses to queries.

    This database ties into the Admin app and stores various fields associated with
    content feedback response to a user's query.
    """

    __tablename__ = "content_feedback"

    content: Mapped["ContentDB"] = relationship("ContentDB")
    content_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("content.content_id", ondelete="CASCADE")
    )
    feedback_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    feedback_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    feedback_sentiment: Mapped[str] = mapped_column(String, nullable=True)
    feedback_text: Mapped[str] = mapped_column(String, nullable=True)
    query: Mapped[QueryDB] = relationship(
        "QueryDB", back_populates="content_feedback", lazy="select"
    )
    query_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("query.query_id", ondelete="CASCADE")
    )
    session_id: Mapped[int] = mapped_column(Integer, nullable=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Construct the string representation of the `ContentFeedbackDB` object.

        Returns
        -------
        str
            A string representation of the `ContentFeedbackDB` object.
        """

        return (
            f"<Feedback #{self.feedback_id} for query "
            f"#{self.query_id}> and content #{self.content_id} {self.feedback_text}"
        )
