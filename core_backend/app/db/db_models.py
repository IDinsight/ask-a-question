from datetime import datetime
from typing import Dict, List, Optional

from litellm import aembedding, embedding
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    func,
    ForeignKey,
    Integer,
    join,
    String,
    delete,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.schema import Index

from ..configs.app_config import EMBEDDING_MODEL, PGVECTOR_VECTOR_SIZE
from ..schemas import (
    ContentTextCreate,
    ContentUpdate,
    FeedbackBase,
    LanguageBase,
    UserQueryBase,
    UserQueryResponse,
    UserQueryResponseError,
    UserQuerySearchResult,
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
    feedback: FeedbackBase,
    asession: AsyncSession,
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
    incoming: WhatsAppIncoming,
    asession: AsyncSession,
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
    response: WhatsAppResponse,
    asession: AsyncSession,
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

    __tablename__ = "contents"

    content_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<Content #{self.content_id}>"


class LanguageDB(Base):
    """
    SQL Alchemy data model for language
    """

    __tablename__ = "languages"

    language_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    language_name: Mapped[str] = mapped_column(String, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index(
            "ix_languages_is_default_true",
            "is_default",
            unique=True,
            postgresql_where=(is_default.is_(True)),
        ),
    )

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<Language #{self.language_id}:  {self.language_name}>"


async def save_language_to_db(
    language: LanguageBase,
    asession: AsyncSession,
) -> LanguageDB:
    """
    Saves a new language in the database
    """

    language_db = LanguageDB(
        language_name=language.language_name,
        is_default=language.is_default,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    )
    asession.add(language_db)

    await asession.commit()
    await asession.refresh(language_db)

    return language_db


async def update_language_in_db(
    language_id: int,
    language: LanguageBase,
    asession: AsyncSession,
) -> LanguageDB:
    """
    Updates a language in the database
    """

    language_db = LanguageDB(
        language_id=language_id,
        is_default=language.is_default,
        language_name=language.language_name,
        updated_datetime_utc=datetime.utcnow(),
    )

    language_db = await asession.merge(language_db)
    await asession.commit()
    return language_db


async def delete_language_from_db(
    language_id: int,
    asession: AsyncSession,
) -> None:
    """
    Deletes a content from the database
    """
    stmt = delete(LanguageDB).where(LanguageDB.language_id == language_id)
    await asession.execute(stmt)
    await asession.commit()


async def get_language_from_db(
    language_id: int,
    asession: AsyncSession,
) -> Optional[LanguageDB]:
    """
    Retrieves a content from the database
    """
    stmt = select(LanguageDB).where(LanguageDB.language_id == language_id)
    language_row = (await asession.execute(stmt)).scalar_one_or_none()
    return language_row


async def get_default_language_from_db(
    asession: AsyncSession,
) -> Optional[LanguageDB]:
    """
    Retrieves a content from the database
    """
    stmt = select(LanguageDB).where(LanguageDB.is_default == True)
    language_row = (await asession.execute(stmt)).scalar_one_or_none()
    return language_row


async def get_list_of_languages_from_db(
    asession: AsyncSession, offset: int = 0, limit: Optional[int] = None
) -> List[LanguageDB]:
    """
    Retrieves all content from the database
    """
    stmt = select(LanguageDB)
    if offset > 0:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    language_rows = (await asession.execute(stmt)).all()

    return [c[0] for c in language_rows] if language_rows else []


async def is_language_name_unique(language_name: str, asession: AsyncSession) -> bool:
    """
    Check if the language name is unique
    """
    stmt = select(LanguageDB).where(LanguageDB.language_name == language_name)
    language_row = (await asession.execute(stmt)).scalar_one_or_none()
    if language_row:
        return False
    else:
        return True


class ContentTextDB(Base):
    """
    SQL Alchemy data model for content text
    """

    __tablename__ = "content_texts"

    content_text_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False
    )
    content_embedding: Mapped[Vector] = mapped_column(
        Vector(int(PGVECTOR_VECTOR_SIZE)), nullable=False
    )

    content_title: Mapped[str] = mapped_column(String(length=150), nullable=False)
    content_text: Mapped[str] = mapped_column(String(length=2000), nullable=False)
    created_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    content_metadata: Mapped[JSONDict] = mapped_column(JSON, nullable=False)

    language_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("languages.language_id"), nullable=False
    )

    content_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contents.content_id"), nullable=False
    )

    language: Mapped["LanguageDB"] = relationship("LanguageDB")

    content: Mapped["ContentDB"] = relationship("ContentDB")

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<ContentText #{self.content_text_id}:  {self.content_text}>"


async def is_content_language_combination_unique(
    content_id: int, language_id: int, asession: AsyncSession
) -> bool:
    """
    Check if the content and language combination is unique
    """
    stmt = select(ContentTextDB).where(
        (ContentTextDB.content_id == content_id)
        & (ContentTextDB.language_id == language_id)
    )
    content_row = (await asession.execute(stmt)).scalar_one_or_none()
    if content_row:
        return False
    else:
        return True


async def save_content_to_db(
    content: ContentTextCreate,
    asession: AsyncSession,
) -> ContentDB:
    """
    Vectorizes and saves a content in the database
    """

    content_embedding = await _get_content_embeddings(content)
    if content.content_id == 0:
        content_db = ContentDB()
        asession.add(content_db)
    else:
        stmt = select(ContentDB).where(ContentDB.content_id == content.content_id)
        content_db = (await asession.execute(stmt)).scalar_one_or_none()

    content_language = await get_language_from_db(content.language_id, asession)
    content_db = ContentTextDB(
        content_embedding=content_embedding,
        content_title=content.content_title,
        content_text=content.content_text,
        language=content_language,
        content=content_db,
        content_metadata=content.content_metadata,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    )

    asession.add(content_db)

    await asession.commit()
    await asession.refresh(content_db)

    return content_db


async def update_content_in_db(
    content_text_id: int,
    content_text: ContentTextCreate,
    asession: AsyncSession,
) -> ContentTextDB:
    """
    Updates a content and vector in the database
    """
    content_embedding = await _get_content_embeddings(content_text)
    language = await get_language_from_db(content_text.language_id, asession)
    content_db = ContentTextDB(
        content_text_id=content_text_id,
        content_embedding=content_embedding,
        content_title=content_text.content_title,
        content_text=content_text.content_text,
        content_id=content_text.content_id,
        language=language,
        content_metadata=content_text.content_metadata,
        updated_datetime_utc=datetime.utcnow(),
    )

    content_db = await asession.merge(content_db)
    await asession.commit()
    return content_db


async def delete_content_from_db(
    content_text_id: int,
    content_id: int,
    asession: AsyncSession,
) -> None:
    """
    Deletes a content from the database
    """
    stmt = delete(ContentTextDB).where(ContentTextDB.content_text_id == content_text_id)
    await asession.execute(stmt)

    stmt = select(ContentTextDB).where(ContentTextDB.content_id == content_id)
    content_row = (await asession.execute(stmt)).first()
    if not content_row:
        stmt = delete(ContentDB).where(ContentDB.content_id == content_id)
        await asession.execute(stmt)
    await asession.commit()


async def get_content_from_db(
    content_text_id: int,
    asession: AsyncSession,
) -> Optional[ContentTextDB]:
    """
    Retrieves a content from the database
    """
    stmt = select(ContentTextDB).where(ContentTextDB.content_text_id == content_text_id)
    content_row = (await asession.execute(stmt)).scalar_one_or_none()
    return content_row


async def get_list_of_content_from_db(
    asession: AsyncSession, offset: int = 0, limit: Optional[int] = None
) -> List[ContentTextDB]:
    """
    Retrieves all contents from the database
    """
    stmt = select(ContentTextDB)
    if offset > 0:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    content_rows = (await asession.execute(stmt)).all()

    return [c[0] for c in content_rows] if content_rows else []


async def get_summary_of_content_from_db(
    asession: AsyncSession,
    language_id: int,
    offset: int = 0,
    limit: Optional[int] = None,
) -> List[ContentTextDB]:
    """
    Get summary of all content from the database in a specific language
    """

    language_subquery = (
        select(
            ContentTextDB.content_id.label("content_id"),
            func.array_agg(LanguageDB.language_name).label("available_languages"),
        )
        .select_from(ContentTextDB)
        .join(LanguageDB, ContentTextDB.language_id == LanguageDB.language_id)
        .group_by(ContentTextDB.content_id)
        .subquery()
    )

    stmt = (
        select(
            ContentTextDB.content_text_id,
            ContentTextDB.content_id,
            ContentTextDB.content_title,
            ContentTextDB.created_datetime_utc,
            ContentTextDB.updated_datetime_utc,
            language_subquery.c.available_languages,
        )
        .join(
            language_subquery,
            ContentTextDB.content_id == language_subquery.c.content_id,
        )
        .where(ContentTextDB.language_id == language_id)
    )

    if offset > 0:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    content_rows = (await asession.execute(stmt)).all()
    return content_rows if content_rows else []


async def get_all_content_from_one_language(
    asession: AsyncSession,
    language_id: int,
    offset: int = 0,
    limit: Optional[int] = None,
) -> List[ContentTextDB]:
    """
    Retrieves all content from the database
    """
    stmt = select(ContentTextDB).where(ContentTextDB.language_id == language_id)
    if offset > 0:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    content_rows = (await asession.execute(stmt)).all()
    return [c[0] for c in content_rows] if content_rows else []


async def get_content_from_content_id_and_language(content_id, language_id, asession):
    """ "
    Retrieves a content from the database using content_id and language_id
    """
    stmt = select(ContentTextDB).where(
        (ContentTextDB.content_id == content_id)
        & (ContentTextDB.language_id == language_id)
    )
    content_row = (await asession.execute(stmt)).scalar_one_or_none()
    return content_row


async def get_all_languages_version_of_content(
    content_id: int,
    asession: AsyncSession,
) -> List[ContentTextDB]:
    """
    Retrieves all content from the database
    """
    stmt = select(ContentTextDB).where(ContentTextDB.content_id == content_id)
    content_rows = (await asession.execute(stmt)).all()
    return [c[0] for c in content_rows] if content_rows else []


async def _get_content_embeddings(
    content: ContentTextCreate | ContentUpdate,
) -> List[float]:
    """
    Vectorizes the content
    """
    text_to_embed = content.content_title + "\n" + content.content_text
    content_embedding = embedding(EMBEDDING_MODEL, text_to_embed).data[0]["embedding"]
    return content_embedding


async def get_similar_content(
    question: UserQueryBase,
    n_similar: int,
    asession: AsyncSession,
) -> Dict[int, UserQuerySearchResult]:
    """
    Get the most similar points in the vector table
    """
    response = embedding(EMBEDDING_MODEL, question.query_text)
    question_embedding = response.data[0]["embedding"]

    return await get_search_results(
        question_embedding,
        n_similar,
        asession,
    )


async def get_similar_content_async(
    question: UserQueryBase, n_similar: int, asession: AsyncSession
) -> Dict[int, UserQuerySearchResult]:
    """
    Get the most similar points in the vector table
    """
    response = await aembedding(EMBEDDING_MODEL, question.query_text)
    question_embedding = response.data[0]["embedding"]

    return await get_search_results(
        question_embedding,
        n_similar,
        asession,
    )


async def get_search_results(
    question_embedding: List[float], n_similar: int, asession: AsyncSession
) -> Dict[int, UserQuerySearchResult]:
    """Get similar content to given embedding and return search results"""
    query = (
        select(
            ContentTextDB,
            ContentTextDB.content_embedding.cosine_distance(question_embedding).label(
                "distance"
            ),
        )
        .order_by(ContentTextDB.content_embedding.cosine_distance(question_embedding))
        .limit(n_similar)
    )
    search_result = (await asession.execute(query)).all()

    results_dict = {}
    for i, r in enumerate(search_result):
        results_dict[i] = UserQuerySearchResult(
            retrieved_title=r[0].content_title,
            retrieved_text=r[0].content_text,
            score=r[1],
        )

    return results_dict
