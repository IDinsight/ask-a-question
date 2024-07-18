"""This module contains the ORM for managing content in the `ContentDB` database and
database helper functions such as saving, updating, deleting, and retrieving content.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    false,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from ..models import Base, JSONDict
from ..schemas import FeedbackSentiment, QuerySearchResult
from ..tags.models import content_tags_table
from ..utils import embedding
from .config import (
    PGVECTOR_DISTANCE,
    PGVECTOR_EF_CONSTRUCTION,
    PGVECTOR_M,
    PGVECTOR_VECTOR_SIZE,
)
from .schemas import (
    ContentCreate,
    ContentUpdate,
)


class ContentDB(Base):
    """ORM for managing content.

    This database ties into the Admin app and allows the user to view, add, edit,
    and delete content in the `content` table.
    """

    __tablename__ = "content"

    __table_args__ = (
        Index(
            "content_idx",
            "content_embedding",
            postgresql_using="hnsw",
            postgresql_with={
                "M": {PGVECTOR_M},
                "ef_construction": {PGVECTOR_EF_CONSTRUCTION},
            },
            postgresql_ops={"embedding": {PGVECTOR_DISTANCE}},
        ),
    )

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

    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    content_tags = relationship(
        "TagDB",
        secondary=content_tags_table,
        back_populates="contents",
    )

    def __repr__(self) -> str:
        """Construct the string representation of the `ContentDB` object.

        :returns:
            A string representation of the `ContentDB` object.
        """

        return (
            f"ContentDB(content_id={self.content_id}, "
            f"user_id={self.user_id}, "
            f"content_embedding=..., "
            f"content_title={self.content_title}, "
            f"content_text={self.content_text}, "
            f"content_metadata={self.content_metadata}, "
            f"content_tags={self.content_tags}, "
            f"created_datetime_utc={self.created_datetime_utc}, "
            f"updated_datetime_utc={self.updated_datetime_utc}), "
            f"is_archived={self.is_archived})"
        )


async def save_content_to_db(
    user_id: int,
    content: ContentCreate,
    asession: AsyncSession,
) -> ContentDB:
    """Vectorize the content and save to the database.

    :param user_id: The ID of the user requesting the save.
    :param content: The content to save.
    :param asession: The `AsyncSession` object to use for the database transaction.

    :returns:
        The content object if it exists, otherwise the newly created content object.
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
    return result or content_db


async def update_content_in_db(
    user_id: int,
    content_id: int,
    content: ContentCreate,
    asession: AsyncSession,
) -> ContentDB:
    """Update content and content embedding in the database.

    :param user_id: The ID of the user requesting the update.
    :param content_id: The ID of the content to update.
    :param content: The content to update.
    :param asession: The `AsyncSession` object to use for the database transaction.

    :returns:
        The content object if it exists, otherwise the newly updated content object.
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
    return result or content_db


async def increment_query_count(
    user_id: int, contents: Dict[int, QuerySearchResult] | None, asession: AsyncSession
) -> None:
    """Increment the query count for the content.

    :param user_id: The ID of the user requesting the query count increment.
    :param contents: The content to increment the query count for.
    :param asession: The `AsyncSession` object to use for the database transaction.
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
    """Delete content from the database.

    NB: Deletion is a soft delete, meaning that the content is not actually removed.
    Instead, the `is_archived` attribute is set to `True`. This will disallow the app
    from retrieving the content for display and future requests, but the content will
    still be available for backend reporting and analysis.

    :param user_id: The ID of the user requesting the deletion.
    :param content_id: The ID of the content to delete.
    :param asession: The `AsyncSession` object to use for the database transaction.
    """

    stmt = (
        update(ContentDB)
        .where(ContentDB.user_id == user_id)
        .where(ContentDB.content_id == content_id)
        .values(is_archived=True)
    )
    await asession.execute(stmt)
    await asession.commit()


async def get_content_from_db(
    user_id: int,
    content_id: int,
    asession: AsyncSession,
) -> Optional[ContentDB]:
    """Retrieve content from the database.

    NB: Database content is only retrieved if the `is_archived` attribute is `False`.

    :param user_id: The ID of the user requesting the content.
    :param content_id: The ID of the content to retrieve.
    :param asession: The `AsyncSession` object to use for the database transaction.

    :returns:
        The content object if it exists, otherwise `None`.
    """

    stmt = (
        select(ContentDB)
        .options(selectinload(ContentDB.content_tags))
        .where(ContentDB.user_id == user_id)
        .where(ContentDB.content_id == content_id)
        .where(ContentDB.is_archived == false())
    )
    content_row = (await asession.execute(stmt)).first()
    return content_row[0] if content_row else None


async def get_list_of_content_from_db(
    user_id: int,
    asession: AsyncSession,
    offset: int = 0,
    limit: Optional[int] = None,
) -> List[ContentDB]:
    """Retrieve all content from the database.

    NB: Database content is only retrieved if the `is_archived` attribute is `False`.

    :param user_id: The ID of the user requesting the content.
    :param asession: The `AsyncSession` object to use for the database transaction.
    :param offset: The number of content items to skip.
    :param limit: The maximum number of content items to retrieve. If not specified,
        then all content items are retrieved.

    :returns:
        A list of content objects if they exist, otherwise an empty list.
    """

    stmt = (
        select(ContentDB)
        .options(selectinload(ContentDB.content_tags))
        .where(ContentDB.user_id == user_id)
        .where(ContentDB.is_archived == false())
        .order_by(ContentDB.content_id)
    )
    if offset > 0:
        stmt = stmt.offset(offset)
    if isinstance(limit, int) and limit > 0:
        stmt = stmt.limit(limit)
    content_rows = (await asession.execute(stmt)).all()

    return [c[0] for c in content_rows] if content_rows else []


async def _get_content_embeddings(
    content: ContentCreate | ContentUpdate,
    metadata: Optional[dict] = None,
) -> List[float]:
    """Vectorize the content.

    :param content: The content to vectorize.
    :param metadata: The metadata to use for the embedding generation.

    :returns:
        The vectorized content embedding.
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
    """Get the most similar points in the vector table.

    :param user_id: The ID of the user requesting the similar content.
    :param question: The question to search for similar content.
    :param n_similar: The number of similar content items to retrieve.
    :param asession: The `AsyncSession` object to use for the database transaction.
    :param metadata: The metadata to use for the embedding generation.

    :returns:
        A dictionary of similar content items if they exist, otherwise an empty
    dictionary
    """

    metadata = metadata or {}
    metadata["generation_name"] = "get_similar_content_async"

    question_embedding = await embedding(question, metadata=metadata)

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
    """Get similar content to given embedding and return search results.

    NB: Database content is only retrieved if the `is_archived` attribute is `False`.

    :param user_id: The ID of the user requesting the content.
    :param question_embedding: The embedding vector of the question to search for.
    :param n_similar: The number of similar content items to retrieve.
    :param asession: The `AsyncSession` object to use for the database transaction.

    :returns:
        results_dict: A dictionary of similar content items if they exist, otherwise an
    empty dictionary.
    """

    query = (
        select(
            ContentDB,
            ContentDB.content_embedding.cosine_distance(question_embedding).label(
                "distance"
            ),
        )
        .where(ContentDB.user_id == user_id)
        .where(ContentDB.is_archived == false())
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
    """Update votes in the database.

    :param user_id: The ID of the user voting.
    :param content_id: The ID of the content to vote on.
    :param vote: The sentiment of the vote.
    :param asession: The `AsyncSession` object to use for the database transaction.

    :returns:
        The content object if it exists, otherwise `None`.
    """

    content_db = await get_content_from_db(
        user_id=user_id, content_id=content_id, asession=asession
    )
    if not content_db:
        return None

    match vote:
        case FeedbackSentiment.POSITIVE:
            content_db.positive_votes += 1
        case FeedbackSentiment.NEGATIVE:
            content_db.negative_votes += 1

    content_db = await asession.merge(content_db)
    await asession.commit()
    return content_db
