"""This module contains ORMs for managing:

1. Questions asked by the user in the `QueryDB` database.
2. Responses sent to the user in the `QueryResponseDB` database.
3. Errors sent to the user in the `QueryResponseErrorDB` database.
4. Response feedback provided by users in the `ResponseFeedbackDB` database.
5. Content feedback provided by users in the `ContentFeedbackDB` database.
"""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..contents.models import ContentDB
from ..models import Base, JSONDict
from ..utils import generate_secret_key
from .schemas import (
    ContentFeedback,
    QueryBase,
    QueryResponse,
    QueryResponseError,
    QuerySearchResult,
    ResponseFeedbackBase,
)


class QueryDB(Base):
    """ORM for managing questions asked by the user.

    This database ties into the Admin app and stores various fields associated with a
    user's query.
    """

    __tablename__ = "query"

    query_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )
    session_id: Mapped[int] = mapped_column(Integer, nullable=True)
    feedback_secret_key: Mapped[str] = mapped_column(String, nullable=False)
    query_text: Mapped[str] = mapped_column(String, nullable=False)
    query_generate_llm_response: Mapped[bool] = mapped_column(Boolean, nullable=False)
    query_metadata: Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    query_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    response_feedback: Mapped[List["ResponseFeedbackDB"]] = relationship(
        "ResponseFeedbackDB", back_populates="query", lazy=True
    )
    content_feedback: Mapped[List["ContentFeedbackDB"]] = relationship(
        "ContentFeedbackDB", back_populates="query", lazy=True
    )
    response: Mapped[List["QueryResponseDB"]] = relationship(
        "QueryResponseDB", back_populates="query", lazy=True
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


async def save_user_query_to_db(
    user_id: int,
    user_query: QueryBase,
    asession: AsyncSession,
) -> QueryDB:
    """Saves a user query to the database alongside generated query_id and feedback
    secret key.

    Parameters
    ----------
    user_id
        The user ID for the organization.
    user_query
        The end user query database object.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    QueryDB
        The user query database object.
    """

    feedback_secret_key = generate_secret_key()
    user_query_db = QueryDB(
        user_id=user_id,
        session_id=user_query.session_id,
        feedback_secret_key=feedback_secret_key,
        query_text=user_query.query_text,
        query_generate_llm_response=user_query.generate_llm_response,
        query_metadata=user_query.query_metadata,
        query_datetime_utc=datetime.now(timezone.utc),
    )
    asession.add(user_query_db)
    await asession.commit()
    await asession.refresh(user_query_db)
    return user_query_db


async def check_secret_key_match(
    secret_key: str, query_id: int, asession: AsyncSession
) -> bool:
    """Check if the secret key matches the one generated for `query_id`.

    Parameters
    ----------
    secret_key
        The secret key.
    query_id
        The query ID.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    bool
        Specifies whether the secret key matches the one generated for `query_id`.
    """

    stmt = select(QueryDB.feedback_secret_key).where(QueryDB.query_id == query_id)
    query_record = (await asession.execute(stmt)).first()
    return (query_record is not None) and (query_record[0] == secret_key)


class QueryResponseDB(Base):
    """ORM for managing responses sent to the user.

    This database ties into the Admin app and stores various fields associated with
    responses to a user's query.
    """

    __tablename__ = "query_response"

    response_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("query.query_id"))
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )
    session_id: Mapped[int] = mapped_column(Integer, nullable=True)
    search_results: Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    llm_response: Mapped[str] = mapped_column(String, nullable=True)
    response_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    debug_info: Mapped[JSONDict] = mapped_column(JSON, nullable=False)
    is_error: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_type: Mapped[str] = mapped_column(String, nullable=True)
    error_message: Mapped[str] = mapped_column(String, nullable=True)

    query: Mapped[QueryDB] = relationship(
        "QueryDB", back_populates="response", lazy=True
    )

    def __repr__(self) -> str:
        """Construct the string representation of the `QueryResponseDB` object.

        Returns
        -------
        str
            A string representation of the `QueryResponseDB` object.
        """

        return f"<Responses for query #{self.query_id}"


async def save_query_response_to_db(
    user_query_db: QueryDB,
    response: QueryResponse | QueryResponseError,
    asession: AsyncSession,
) -> QueryResponseDB:
    """Saves the user query response to the database.

    Parameters
    ----------
    user_query_db
        The user query database object.
    response
        The query response object.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    QueryResponseDB
        The user query response database object.
    """
    if type(response) is QueryResponse:
        user_query_responses_db = QueryResponseDB(
            query_id=user_query_db.query_id,
            user_id=user_query_db.user_id,
            session_id=user_query_db.session_id,
            search_results=response.model_dump()["search_results"],
            llm_response=response.model_dump()["llm_response"],
            response_datetime_utc=datetime.now(timezone.utc),
            debug_info=response.model_dump()["debug_info"],
            is_error=False,
        )
    elif type(response) is QueryResponseError:
        user_query_responses_db = QueryResponseDB(
            query_id=user_query_db.query_id,
            user_id=user_query_db.user_id,
            session_id=user_query_db.session_id,
            search_results=response.model_dump()["search_results"],
            llm_response=response.model_dump()["llm_response"],
            response_datetime_utc=datetime.now(timezone.utc),
            debug_info=response.model_dump()["debug_info"],
            is_error=True,
            error_type=response.error_type,
            error_message=response.error_message,
        )
    else:
        raise ValueError("Invalid response type.")

    asession.add(user_query_responses_db)
    await asession.commit()
    await asession.refresh(user_query_responses_db)
    return user_query_responses_db


class QueryResponseContentDB(Base):
    """
    ORM for storing what content was returned for a given query.
    Allows us to track how many times a given content was returned in a time period.
    """

    __tablename__ = "query_response_content"

    content_for_query_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )
    session_id: Mapped[int] = mapped_column(Integer, nullable=True)
    query_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("query.query_id"), nullable=False
    )
    content_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("content.content_id"), nullable=False
    )
    created_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("idx_user_id_created_datetime", "user_id", "created_datetime_utc"),
    )

    def __repr__(self) -> str:
        """
        Construct the string representation of the `QueryResponseContentDB` object.

        Returns
        -------
        str
            A string representation of the `QueryResponseContentDB` object.
        """

        return (
            f"ContentForQueryDB(content_for_query_id={self.content_for_query_id}, "
            f"user_id={self.user_id}, "
            f"session_id={self.session_id}, "
            f"content_id={self.content_id}, "
            f"query_id={self.query_id}, "
            f"created_datetime_utc={self.created_datetime_utc})"
        )


async def save_content_for_query_to_db(
    user_id: int,
    session_id: int | None,
    query_id: int,
    contents: dict[int, QuerySearchResult] | None,
    asession: AsyncSession,
) -> None:
    """
    Saves the content returned for a query to the database.
    """

    if contents is None:
        return

    for content in contents.values():
        content_for_query_db = QueryResponseContentDB(
            user_id=user_id,
            session_id=session_id,
            query_id=query_id,
            content_id=content.id,
            created_datetime_utc=datetime.now(timezone.utc),
        )
        asession.add(content_for_query_db)
    await asession.commit()


class ResponseFeedbackDB(Base):
    """ORM for managing feedback provided by user for AI responses to queries.

    This database ties into the Admin app and stores various fields associated with AI
    feedback response to a user's query.
    """

    __tablename__ = "query_response_feedback"

    feedback_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    feedback_sentiment: Mapped[str] = mapped_column(String, nullable=True)
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("query.query_id"))
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )
    session_id: Mapped[int] = mapped_column(Integer, nullable=True)
    feedback_text: Mapped[str] = mapped_column(String, nullable=True)
    feedback_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    query: Mapped[QueryDB] = relationship(
        "QueryDB", back_populates="response_feedback", lazy=True
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


async def save_response_feedback_to_db(
    feedback: ResponseFeedbackBase,
    asession: AsyncSession,
) -> ResponseFeedbackDB:
    """Saves feedback to the database.

    Parameters
    ----------
    feedback
        The response feedback object.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    ResponseFeedbackDB
        The response feedback database object.
    """
    # Fetch user_id from the query table
    result = await asession.execute(
        select(QueryDB.user_id).where(QueryDB.query_id == feedback.query_id)
    )
    user_id = result.scalar_one()

    response_feedback_db = ResponseFeedbackDB(
        feedback_datetime_utc=datetime.now(timezone.utc),
        feedback_sentiment=feedback.feedback_sentiment,
        query_id=feedback.query_id,
        user_id=user_id,
        session_id=feedback.session_id,
        feedback_text=feedback.feedback_text,
    )
    asession.add(response_feedback_db)
    await asession.commit()
    await asession.refresh(response_feedback_db)
    return response_feedback_db


class ContentFeedbackDB(Base):
    """ORM for managing feedback provided by user for content responses to queries.

    This database ties into the Admin app and stores various fields associated with
    content feedback response to a user's query.
    """

    __tablename__ = "content_feedback"

    feedback_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    feedback_sentiment: Mapped[str] = mapped_column(String, nullable=True)
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("query.query_id"))
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )
    session_id: Mapped[int] = mapped_column(Integer, nullable=True)
    feedback_text: Mapped[str] = mapped_column(String, nullable=True)
    feedback_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    content_id: Mapped[int] = mapped_column(Integer, ForeignKey("content.content_id"))

    query: Mapped[QueryDB] = relationship(
        "QueryDB", back_populates="content_feedback", lazy=True
    )

    content: Mapped["ContentDB"] = relationship("ContentDB")

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


async def save_content_feedback_to_db(
    feedback: ContentFeedback,
    asession: AsyncSession,
) -> ContentFeedbackDB:
    """Saves feedback to the database.

    Parameters
    ----------
    feedback
        The content feedback object.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    ContentFeedbackDB
        The content feedback database object.
    """
    # Fetch user_id from the query table
    result = await asession.execute(
        select(QueryDB.user_id).where(QueryDB.query_id == feedback.query_id)
    )
    user_id = result.scalar_one()

    content_feedback_db = ContentFeedbackDB(
        feedback_datetime_utc=datetime.now(timezone.utc),
        feedback_sentiment=feedback.feedback_sentiment,
        query_id=feedback.query_id,
        user_id=user_id,
        session_id=feedback.session_id,
        feedback_text=feedback.feedback_text,
        content_id=feedback.content_id,
    )
    asession.add(content_feedback_db)
    await asession.commit()
    await asession.refresh(content_feedback_db)
    return content_feedback_db
