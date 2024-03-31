from datetime import datetime
from datetime import timezone as tz
from typing import Dict, List, Optional, Sequence

from litellm import aembedding, embedding
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    Row,
    String,
    delete,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..config import EMBEDDING_MODEL
from ..contents.config import PGVECTOR_VECTOR_SIZE
from ..languages.models import LanguageDB, get_language_from_db
from ..models import Base, JSONDict
from .schemas import (
    ContentTextCreate,
)


class ContentDB(Base):
    """
    SQL Alchemy data model for content
    """

    __tablename__ = "contents"

    content_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    def __repr__(self) -> str:
        """Pretty Print"""
        return f"<Content #{self.content_id}>"


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
    content_id: int | None, language_id: int, asession: AsyncSession
) -> bool:
    """
    Check if the content and language combination is unique
    """
    if not content_id:
        return True
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
) -> ContentTextDB:
    """
    Vectorizes and saves a content in the database
    """

    content_embedding = await _get_content_embeddings(
        content.content_title, content.content_text
    )
    stmt = select(ContentDB).where(ContentDB.content_id == content.content_id)
    content_db = (await asession.execute(stmt)).scalar_one_or_none()
    if not content_db:
        content_db = ContentDB()
        asession.add(content_db)

    content_language = await get_language_from_db(content.language_id, asession)
    content_text_db = ContentTextDB(
        content_embedding=content_embedding,
        content_title=content.content_title,
        content_text=content.content_text,
        language=content_language,
        content=content_db,
        content_metadata=content.content_metadata,
        created_datetime_utc=datetime.now(tz.utc).replace(tzinfo=None),
        updated_datetime_utc=datetime.now(tz.utc).replace(tzinfo=None),
    )

    asession.add(content_text_db)

    await asession.commit()
    await asession.refresh(content_text_db)

    return content_text_db


async def update_content_in_db(
    old_content: ContentTextDB,
    content_text: ContentTextCreate,
    asession: AsyncSession,
) -> ContentTextDB:
    """
    Updates a content and vector in the database
    """
    content_embedding = await _get_content_embeddings(
        content_text.content_title, content_text.content_text
    )
    language = await get_language_from_db(content_text.language_id, asession)
    content_text_db = ContentTextDB(
        content_text_id=old_content.content_text_id,
        content_embedding=content_embedding,
        content_title=content_text.content_title,
        content_text=content_text.content_text,
        content_id=content_text.content_id,
        language=language,
        content_metadata=content_text.content_metadata,
        created_datetime_utc=old_content.created_datetime_utc,
        updated_datetime_utc=datetime.now(tz.utc).replace(tzinfo=None),
    )

    content_text_db = await asession.merge(content_text_db)
    if content_text_db.content_id != old_content.content_id:
        old_contents = await get_all_languages_version_of_content(
            old_content.content_id, asession
        )
        if len(old_contents) < 1:
            stmt = delete(ContentDB).where(
                ContentDB.content_id == old_content.content_id
            )
            await asession.execute(stmt)

    await asession.commit()
    return content_text_db


async def delete_content_from_db(
    content_id: int,
    asession: AsyncSession,
    language_id: Optional[int] = None,
) -> None:
    """
    Deletes a content  from the database
    """
    if language_id:
        stmt = delete(ContentTextDB).where(
            (ContentTextDB.content_id == content_id)
            & (ContentTextDB.language_id == language_id)
        )
    else:
        stmt = delete(ContentTextDB).where(ContentTextDB.content_id == content_id)
    await asession.execute(stmt)

    content_stmt = select(ContentDB).where(ContentDB.content_id == content_id)
    content_row = (await asession.execute(content_stmt)).scalar_one_or_none()
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


async def get_landing_view_of_content_from_db(
    asession: AsyncSession,
    language_id: int,
    offset: int = 0,
    limit: Optional[int] = None,
) -> Sequence[Row]:
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
            ContentTextDB.content_text,
            ContentTextDB.created_datetime_utc,
            ContentTextDB.updated_datetime_utc,
            language_subquery.c.available_languages,
        )
        .join(
            language_subquery,
            ContentTextDB.content_id == language_subquery.c.content_id,
        )
        .where(ContentTextDB.language_id == language_id)
        .order_by(ContentTextDB.content_id)
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


async def get_content_from_content_id_and_language(
    content_id: int, language_id: int, asession: AsyncSession
) -> ContentTextDB | None:
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


async def _get_content_embeddings(content_title: str, content_text: str) -> List[float]:
    """
    Vectorizes the content
    """
    text_to_embed = content_title + "\n" + content_text
    content_embedding = embedding(EMBEDDING_MODEL, text_to_embed).data[0]["embedding"]
    return content_embedding


async def get_similar_content(
    question: str,
    n_similar: int,
    asession: AsyncSession,
) -> Dict[int, tuple[str, str, float]]:
    """
    Get the most similar points in the vector table
    """
    response = embedding(EMBEDDING_MODEL, question)
    question_embedding = response.data[0]["embedding"]

    return await get_search_results(
        question_embedding,
        n_similar,
        asession,
    )


async def get_similar_content_async(
    question: str, n_similar: int, asession: AsyncSession
) -> Dict[int, tuple[str, str, float]]:
    """
    Get the most similar points in the vector table
    """
    response = await aembedding(EMBEDDING_MODEL, question)
    question_embedding = response.data[0]["embedding"]

    return await get_search_results(
        question_embedding,
        n_similar,
        asession,
    )


async def get_search_results(
    question_embedding: List[float], n_similar: int, asession: AsyncSession
) -> Dict[int, tuple[str, str, float]]:
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
        results_dict[i] = (r[0].content_title, r[0].content_text, r[1])

    return results_dict
