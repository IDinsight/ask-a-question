from datetime import datetime
from typing import Dict, List, Optional

from litellm import embedding
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ..configs.app_config import EMBEDDING_MODEL, PGVECTOR_VECTOR_SIZE
from ..configs.llm_prompts import IdentifiedLanguage
from ..schemas import (
    ContentCreate,
    ContentUpdate,
    FeedbackBase,
    UserQueryBase,
    UserQueryResponse,
    UserQueryResponseError,
    WhatsAppIncoming,
    WhatsAppResponse,
)

JSONDict = Dict[str, str]


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models"""

    pass


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

    feedback: Mapped[List["FeedbackDB"]] = relationship(
        "FeedbackDB", back_populates="query", lazy=True
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
    asession: AsyncSession, feedback_secret_key: str, user_query: UserQueryBase
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
    asession: AsyncSession,
    user_query_db: UserQueryDB,
    response: UserQueryResponse,
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
    asession: AsyncSession,
    user_query_db: UserQueryDB,
    error: UserQueryResponseError,
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


class FeedbackDB(Base):
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

    query: Mapped[UserQueryDB] = relationship(
        "UserQueryDB", back_populates="feedback", lazy=True
    )

    def __repr__(self) -> str:
        """Pretty Print"""
        return (
            f"<Feedback #{self.feedback_id} for query "
            f"#{self.query_id}> {self.feedback_text}"
        )


async def save_feedback_to_db(
    asession: AsyncSession, feedback: FeedbackBase
) -> FeedbackDB:
    """
    Saves feedback to the database.
    """
    feedback_db = FeedbackDB(
        feedback_datetime_utc=datetime.utcnow(),
        query_id=feedback.query_id,
        feedback_text=feedback.feedback_text,
    )
    asession.add(feedback_db)
    await asession.commit()
    await asession.refresh(feedback_db)
    return feedback_db


class WhatsAppMessageDB(Base):
    """
    SQL Alchemy data model for incoming messages from user.
    """

    __tablename__ = "whatsapp_incoming_messages"

    incoming_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    msg_id_from_whatsapp: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    phonenumber_id: Mapped[str] = mapped_column(String, nullable=False)
    incoming_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    response = relationship(
        "WhatsAppResponseDB", back_populates="incoming_message", lazy=True
    )


class WhatsAppResponseDB(Base):
    """
    SQL Alchemy data model for responses sent to user.
    """

    __tablename__ = "whatsapp_responses"

    response_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    incoming_id = mapped_column(
        Integer, ForeignKey("whatsapp_incoming_messages.incoming_id"), nullable=False
    )
    response = mapped_column(String)
    response_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    incoming_message = relationship(
        "WhatsAppMessageDB", back_populates="response", lazy=True
    )


async def save_wamessage_to_db(
    asession: AsyncSession,
    incoming: WhatsAppIncoming,
) -> WhatsAppMessageDB:
    """
    Saves WhatsApp incoming messages to the database.
    """
    wa_incoming = WhatsAppMessageDB(
        phone_number=incoming.phone_number,
        msg_id_from_whatsapp=incoming.msg_id_from_whatsapp,
        message=incoming.message,
        phonenumber_id=incoming.phone_id,
        incoming_datetime_utc=datetime.utcnow(),
    )
    asession.add(wa_incoming)
    await asession.commit()
    await asession.refresh(wa_incoming)
    return wa_incoming


async def save_waresponse_to_db(
    asession: AsyncSession,
    response: WhatsAppResponse,
) -> WhatsAppResponseDB:
    """
    Saves WhatsApp responses to the database.
    """
    wa_response = WhatsAppResponseDB(
        incoming_id=response.incoming_id,
        response=response.response_text,
        response_datetime_utc=datetime.utcnow(),
        response_status=response.response_status,
    )
    asession.add(wa_response)
    await asession.commit()
    await asession.refresh(wa_response)
    return wa_response


class ContentDB(Base):
    """
    SQL Alchemy data model for content
    """

    __tablename__ = "content"

    content_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    content_embedding: Mapped[Vector] = mapped_column(
        Vector(PGVECTOR_VECTOR_SIZE), nullable=False
    )
    content_title: Mapped[str] = mapped_column(String, nullable=False)
    content_text: Mapped[str] = mapped_column(String, nullable=False)
    content_language: Mapped[str] = mapped_column(
        Enum(IdentifiedLanguage), nullable=False
    )

    content_metadata: Mapped[JSONDict] = mapped_column(JSON, nullable=False)

    created_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<Content #{self.content_id}:  {self.content_text}>"


async def save_content_to_db(
    asession: AsyncSession, content: ContentCreate
) -> ContentDB:
    """
    Vectorizes and saves a content in the database
    """

    content_embedding = _get_content_embeddings(content)
    content_db = ContentDB(
        content_embedding=content_embedding,
        content_title=content.content_title,
        content_text=content.content_text,
        content_language=content.content_language,
        content_metadata=content.content_metadata,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    )

    asession.add(content_db)
    await asession.commit()
    await asession.refresh(content_db)
    return content_db


async def update_content_in_db(
    asession: AsyncSession, content: ContentUpdate
) -> ContentDB:
    """
    Updates a content and vector in the database
    """

    content_embedding = _get_content_embeddings(content)
    content_db = ContentDB(
        content_id=content.content_id,
        content_embedding=content_embedding,
        content_title=content.content_title,
        content_text=content.content_text,
        content_language=content.content_language,
        content_metadata=content.content_metadata,
        updated_datetime_utc=datetime.utcnow(),
    )

    content_db = await asession.merge(content_db)
    await asession.commit()
    return content_db


async def delete_content_from_db(asession: AsyncSession, content_id: int) -> None:
    """
    Deletes a content from the database
    """
    stmt = delete(ContentDB).where(ContentDB.content_id == content_id)
    await asession.execute(stmt)
    await asession.commit()


async def get_content_from_db(
    asession: AsyncSession, content_id: int
) -> Optional[ContentDB]:
    """
    Retrieves a content from the database
    """
    stmt = select(ContentDB).where(ContentDB.content_id == content_id)
    content_row = (await asession.execute(stmt)).first()
    if content_row:
        return content_row[0]
    else:
        return None


async def get_list_of_content_from_db(
    asession: AsyncSession, offset: int = 0, limit: Optional[int] = None
) -> List[ContentDB]:
    """
    Retrieves all content from the database
    """
    stmt = select(ContentDB)
    if offset > 0:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    content_rows = (await asession.execute(stmt)).all()

    return [c[0] for c in content_rows] if content_rows else []


async def _get_content_embeddings(
    content: ContentCreate | ContentUpdate,
) -> List[float]:
    """
    Vectorizes the content
    """
    text_to_embed = content.content_title + "\n" + content.content_text
    content_embedding = embedding(EMBEDDING_MODEL, text_to_embed).data[0]["embedding"]
    return content_embedding
