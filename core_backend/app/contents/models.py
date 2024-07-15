from datetime import datetime
from typing import Dict, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    delete,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from ..models import Base, JSONDict
from ..schemas import FeedbackSentiment, QuerySearchResult
from ..tags.models import content_tags_table
from ..utils import embedding
from .config import PGVECTOR_VECTOR_SIZE
from .schemas import (
    ContentCreate,
    ContentUpdate,
)


class ContentDB(Base):
    """
    SQL Alchemy data model for content
    """

    __tablename__ = "content"

    content_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )

    content_embedding: Mapped[Vector] = mapped_column(
        Vector(int(PGVECTOR_VECTOR_SIZE)), nullable=False
    )
    content_title: Mapped[str] = mapped_column(String(length=150), nullable=False)
    content_text: Mapped[str] = mapped_column(String(length=2000), nullable=False)

    content_metadata: Mapped[JSONDict] = mapped_column(JSON, nullable=False)

    created_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    positive_votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negative_votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    query_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    content_tags = relationship(
        "TagDB",
        secondary=content_tags_table,
        back_populates="contents",
    )

    def __repr__(self) -> str:
        """Pretty Print"""
        return (
            f"ContentDB(content_id={self.content_id}, "
            f"user_id={self.user_id}, "
            f"content_embedding=..., "
            f"content_title={self.content_title}, "
            f"content_text={self.content_text}, "
            f"content_metadata={self.content_metadata}, "
            f"content_tags={self.content_tags}, "
            f"created_datetime_utc={self.created_datetime_utc}, "
            f"updated_datetime_utc={self.updated_datetime_utc})"
        )


async def save_content_to_db(
    user_id: int,
    content: ContentCreate,
    asession: AsyncSession,
) -> ContentDB:
    """
    Vectorizes and saves a content in the database
    """
    metadata = {
        "trace_user_id": "user_id-" + str(user_id),
        "generation_name": "save_content_to_db",
    }

    content_embedding = await _get_content_embeddings(content, metadata=metadata)
    content_db = ContentDB(
        user_id=user_id,
        content_embedding=content_embedding,
        content_title=content.content_title,
        content_text=content.content_text,
        content_metadata=content.content_metadata,
        content_tags=content.content_tags,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    )
    asession.add(content_db)

    await asession.commit()
    await asession.refresh(content_db)

    result = await get_content_from_db(
        content_db.user_id, content_db.content_id, asession
    )
    if result:
        return result
    else:
        return content_db


async def update_content_in_db(
    user_id: int,
    content_id: int,
    content: ContentCreate,
    asession: AsyncSession,
) -> ContentDB:
    """
    Updates a content and vector in the database
    """
    metadata = {
        "trace_user_id": "user_id-" + str(user_id),
        "generation_name": "update_content_in_db",
    }

    content_embedding = await _get_content_embeddings(content, metadata=metadata)
    content_db = ContentDB(
        content_id=content_id,
        user_id=user_id,
        content_embedding=content_embedding,
        content_title=content.content_title,
        content_text=content.content_text,
        content_metadata=content.content_metadata,
        content_tags=content.content_tags,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    )

    content_db = await asession.merge(content_db)
    await asession.commit()
    await asession.refresh(content_db)
    result = await get_content_from_db(
        content_db.user_id, content_db.content_id, asession
    )
    if result:
        return result
    else:
        return content_db


async def increment_query_count(
    user_id: int, contents: Dict[int, QuerySearchResult] | None, asession: AsyncSession
) -> None:
    """
    Increments the query count for the content
    """
    if contents is None:
        return
    for _, content in contents.items():
        content_db = await get_content_from_db(
            user_id=user_id, content_id=content.retrieved_content_id, asession=asession
        )
        if content_db:
            content_db.query_count = content_db.query_count + 1
            await asession.merge(content_db)
    await asession.commit()


async def delete_content_from_db(
    user_id: int,
    content_id: int,
    asession: AsyncSession,
) -> None:
    """
    Deletes a content from the database
    """
    association_stmt = delete(content_tags_table).where(
        content_tags_table.c.content_id == content_id
    )
    await asession.execute(association_stmt)
    stmt = (
        delete(ContentDB)
        .where(ContentDB.user_id == user_id)
        .where(ContentDB.content_id == content_id)
    )
    await asession.execute(stmt)
    await asession.commit()


async def get_content_from_db(
    user_id: int,
    content_id: int,
    asession: AsyncSession,
) -> Optional[ContentDB]:
    """
    Retrieves a content from the database
    """
    stmt = (
        select(ContentDB)
        .options(selectinload(ContentDB.content_tags))
        .where(ContentDB.user_id == user_id)
        .where(ContentDB.content_id == content_id)
    )
    content_row = (await asession.execute(stmt)).first()
    if content_row:
        return content_row[0]
    else:
        return None


async def get_list_of_content_from_db(
    user_id: int,
    asession: AsyncSession,
    offset: int = 0,
    limit: Optional[int] = None,
) -> List[ContentDB]:
    """
    Retrieves all content from the database
    """
    stmt = (
        select(ContentDB)
        .options(selectinload(ContentDB.content_tags))
        .where(ContentDB.user_id == user_id)
        .order_by(ContentDB.content_id)
    )
    if offset > 0:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    content_rows = (await asession.execute(stmt)).all()

    return [c[0] for c in content_rows] if content_rows else []


async def _get_content_embeddings(
    content: ContentCreate | ContentUpdate,
    metadata: Optional[dict] = None,
) -> List[float]:
    """
    Vectorizes the content
    """
    text_to_embed = content.content_title + "\n" + content.content_text
    return await embedding(text_to_embed, metadata=metadata)


async def get_similar_content_async(
    user_id: int,
    question: str,
    n_similar: int,
    asession: AsyncSession,
    metadata: Optional[dict] = None,
) -> Dict[int, tuple[str, str, int, float]]:
    """
    Get the most similar points in the vector table
    """
    if metadata is None:
        metadata = {}
    if metadata is not None:
        metadata["generation_name"] = "get_similar_content_async"

    question_embedding = await embedding(
        question,
        metadata=metadata,
    )

    return await get_search_results(
        user_id=user_id,
        question_embedding=question_embedding,
        n_similar=n_similar,
        asession=asession,
    )


async def get_search_results(
    user_id: int,
    question_embedding: List[float],
    n_similar: int,
    asession: AsyncSession,
) -> Dict[int, tuple[str, str, int, float]]:
    """Get similar content to given embedding and return search results"""
    query = (
        select(
            ContentDB,
            ContentDB.content_embedding.cosine_distance(question_embedding).label(
                "distance"
            ),
        )
        .where(ContentDB.user_id == user_id)
        .order_by(ContentDB.content_embedding.cosine_distance(question_embedding))
        .limit(n_similar)
    )
    search_result = (await asession.execute(query)).all()

    results_dict = {}
    for i, r in enumerate(search_result):
        results_dict[i] = (r[0].content_title, r[0].content_text, r[0].content_id, r[1])

    return results_dict


async def update_votes_in_db(
    user_id: int,
    content_id: int,
    vote: str,
    asession: AsyncSession,
) -> Optional[ContentDB]:
    """
    Updates the votes in the database
    """

    content_db = await get_content_from_db(
        user_id=user_id, content_id=content_id, asession=asession
    )
    if not content_db:
        return None
    else:
        if vote == FeedbackSentiment.POSITIVE:
            content_db.positive_votes = content_db.positive_votes + 1
        elif vote == FeedbackSentiment.NEGATIVE:
            content_db.negative_votes = content_db.negative_votes + 1

    content_db = await asession.merge(content_db)
    await asession.commit()
    return content_db
