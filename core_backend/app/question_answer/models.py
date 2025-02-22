"""This module contains ORMs for managing:

1. Questions asked by the user in the `QueryDB` database.
2. Responses sent to the user in the `QueryResponseDB` database.
3. Errors sent to the user in the `QueryResponseErrorDB` database.
4. Response feedback provided by users in the `ResponseFeedbackDB` database.
5. Content feedback provided by users in the `ContentFeedbackDB` database.
"""

from datetime import datetime, timezone

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
    QueryAudioResponse,
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

    content_feedback: Mapped[list["ContentFeedbackDB"]] = relationship(
        "ContentFeedbackDB", back_populates="query", lazy=True
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
        "QueryResponseDB", back_populates="query", lazy=True
    )
    response_feedback: Mapped[list["ResponseFeedbackDB"]] = relationship(
        "ResponseFeedbackDB", back_populates="query", lazy=True
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
        "QueryDB", back_populates="response", lazy=True
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
        "QueryDB", back_populates="response_feedback", lazy=True
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
        "QueryDB", back_populates="content_feedback", lazy=True
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


async def check_secret_key_match(
    *, asession: AsyncSession, query_id: int, secret_key: str
) -> bool:
    """Check if the secret key matches the one generated for `query_id`.

    Parameters
    ----------
    asession
        `AsyncSession` object for database transactions.
    query_id
        The query ID.
    secret_key
        The secret key.

    Returns
    -------
    bool
        Specifies whether the secret key matches the one generated for `query_id`.
    """

    stmt = select(QueryDB.feedback_secret_key).where(QueryDB.query_id == query_id)
    query_record = (await asession.execute(stmt)).first()
    return (query_record is not None) and (query_record[0] == secret_key)


async def save_content_feedback_to_db(
    *, asession: AsyncSession, feedback: ContentFeedback
) -> ContentFeedbackDB:
    """Saves feedback to the database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    feedback
        The content feedback object.

    Returns
    -------
    ContentFeedbackDB
        The content feedback database object.
    """

    # Fetch workspace ID from the query table.
    result = await asession.execute(
        select(QueryDB.workspace_id).where(QueryDB.query_id == feedback.query_id)
    )
    workspace_id = result.scalar_one()

    content_feedback_db = ContentFeedbackDB(
        content_id=feedback.content_id,
        feedback_datetime_utc=datetime.now(timezone.utc),
        feedback_sentiment=feedback.feedback_sentiment,
        feedback_text=feedback.feedback_text,
        query_id=feedback.query_id,
        session_id=feedback.session_id,
        workspace_id=workspace_id,
    )
    asession.add(content_feedback_db)
    await asession.commit()
    await asession.refresh(content_feedback_db)
    return content_feedback_db


async def save_content_for_query_to_db(
    *,
    asession: AsyncSession,
    contents: dict[int, QuerySearchResult] | None,
    query_id: int,
    session_id: int | None,
    workspace_id: int,
) -> None:
    """Save the content returned for a query to the database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    contents
        The contents to save to the database.
    query_id
        The ID of the query.
    session_id
        The ID of the session.
    workspace_id
        The ID of the workspace containing the contents to save.
    """

    if contents is None:
        return
    all_records = []
    for content in contents.values():
        all_records.append(
            QueryResponseContentDB(
                content_id=content.id,
                created_datetime_utc=datetime.now(timezone.utc),
                query_id=query_id,
                session_id=session_id,
                workspace_id=workspace_id,
            )
        )
    asession.add_all(all_records)
    await asession.commit()


async def save_query_response_to_db(
    *,
    asession: AsyncSession,
    response: QueryResponse | QueryAudioResponse | QueryResponseError,
    user_query_db: QueryDB,
    workspace_id: int,
) -> QueryResponseDB:
    """Saves the user query response to the database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    response
        The query response object.
    user_query_db
        The user query database object.
    workspace_id
        The ID of the workspace containing the contents used for the query response.

    Returns
    -------
    QueryResponseDB
        The user query response database object.

    Raises
    ------
    ValueError
        If the response type is invalid.
    """

    if isinstance(response, QueryResponseError):
        user_query_responses_db = QueryResponseDB(
            debug_info=response.model_dump()["debug_info"],
            error_message=response.error_message,
            error_type=response.error_type,
            is_error=True,
            query_id=user_query_db.query_id,
            llm_response=response.model_dump()["llm_response"],
            response_datetime_utc=datetime.now(timezone.utc),
            search_results=response.model_dump()["search_results"],
            session_id=user_query_db.session_id,
            tts_filepath=None,
            workspace_id=workspace_id,
        )
    elif isinstance(response, QueryAudioResponse):
        user_query_responses_db = QueryResponseDB(
            debug_info=response.model_dump()["debug_info"],
            is_error=False,
            llm_response=response.model_dump()["llm_response"],
            query_id=user_query_db.query_id,
            response_datetime_utc=datetime.now(timezone.utc),
            search_results=response.model_dump()["search_results"],
            session_id=user_query_db.session_id,
            tts_filepath=response.model_dump()["tts_filepath"],
            workspace_id=workspace_id,
        )
    elif isinstance(response, QueryResponse):
        user_query_responses_db = QueryResponseDB(
            debug_info=response.model_dump()["debug_info"],
            is_error=False,
            llm_response=response.model_dump()["llm_response"],
            query_id=user_query_db.query_id,
            response_datetime_utc=datetime.now(timezone.utc),
            search_results=response.model_dump()["search_results"],
            session_id=user_query_db.session_id,
            workspace_id=workspace_id,
        )
    else:
        raise ValueError("Invalid response type.")

    asession.add(user_query_responses_db)
    await asession.commit()
    await asession.refresh(user_query_responses_db)
    return user_query_responses_db


async def save_response_feedback_to_db(
    *, asession: AsyncSession, feedback: ResponseFeedbackBase
) -> ResponseFeedbackDB:
    """Save feedback to the database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    feedback
        The response feedback object.

    Returns
    -------
    ResponseFeedbackDB
        The response feedback database object.
    """

    # Fetch workspace ID from the query table.
    result = await asession.execute(
        select(QueryDB.workspace_id).where(QueryDB.query_id == feedback.query_id)
    )
    workspace_id = result.scalar_one()

    response_feedback_db = ResponseFeedbackDB(
        feedback_datetime_utc=datetime.now(timezone.utc),
        feedback_sentiment=feedback.feedback_sentiment,
        feedback_text=feedback.feedback_text,
        query_id=feedback.query_id,
        session_id=feedback.session_id,
        workspace_id=workspace_id,
    )
    asession.add(response_feedback_db)
    await asession.commit()
    await asession.refresh(response_feedback_db)
    return response_feedback_db


async def save_user_query_to_db(
    *, asession: AsyncSession, user_query: QueryBase, workspace_id: int
) -> QueryDB:
    """Saves a user query to the database alongside the generated feedback secret key.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_query
        The end user query database object.
    workspace_id
        The ID of the workspace containing the contents that the query will be
        executed against.

    Returns
    -------
    QueryDB
        The user query database object.
    """

    feedback_secret_key = generate_secret_key()
    user_query_db = QueryDB(
        feedback_secret_key=feedback_secret_key,
        query_datetime_utc=datetime.now(timezone.utc),
        query_generate_llm_response=user_query.generate_llm_response,
        query_metadata=user_query.query_metadata,
        query_text=user_query.query_text,
        session_id=user_query.session_id,
        workspace_id=workspace_id,
    )
    asession.add(user_query_db)
    await asession.commit()
    await asession.refresh(user_query_db)
    return user_query_db
