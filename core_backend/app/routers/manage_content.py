from datetime import datetime
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from litellm import embedding
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_fullaccess_user, get_current_readonly_user
from ..configs.app_config import EMBEDDING_MODEL, QDRANT_COLLECTION_NAME
from ..db.db_models import (
    ContentDB,
    delete_content_from_db,
    get_content_from_db,
    get_list_of_content_from_db,
    save_content_to_db,
    update_content_in_db,
)
from ..db.engine import get_async_session
from ..schemas import AuthenticatedUser, ContentCreate, ContentRetrieve
from ..utils import setup_logger

router = APIRouter(prefix="/content")
logger = setup_logger()


class QdrantPayload(BaseModel):
    """Content payload for qdrant"""

    # Ensure len("*{title}*\n\n{text}") <= 1600
    content_title: Annotated[str, StringConstraints(max_length=150)]
    content_text: Annotated[str, StringConstraints(max_length=1446)]

    content_metadata: dict = Field(default_factory=dict)
    created_datetime_utc: datetime = Field(default_factory=datetime.utcnow)
    updated_datetime_utc: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(extra="allow")


@router.post("/create", response_model=ContentRetrieve)
async def create_content(
    content: ContentCreate,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve | None:
    """
    Create content endpoint. Calls embedding model to get content embedding and
    upserts it to PG database
    """

    content_db = await save_content_to_db(asession, content)
    return _convert_record_to_schema(content_db)


@router.put("/{content_id}/edit", response_model=ContentRetrieve)
async def edit_content(
    content_id: int,
    content: ContentCreate,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve:
    """
    Edit content endpoint
    """
    old_content = await get_content_from_db(asession, content_id)

    if not old_content:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_id}` not found"
        )
    updated_content = await update_content_in_db(asession, content_id, content)

    return _convert_record_to_schema(updated_content)


@router.get("/list", response_model=list[ContentRetrieve])
async def retrieve_content(
    readonly_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_readonly_user)
    ],
    skip: int = 0,
    limit: int = 50,
    asession: AsyncSession = Depends(get_async_session),
) -> List[ContentRetrieve]:
    """
    Retrieve all content endpoint
    """
    records = await get_list_of_content_from_db(asession, skip, limit)
    contents = [_convert_record_to_schema(c) for c in records]
    return contents


@router.delete("/{content_id}/delete")
async def delete_content(
    content_id: int,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Delete content endpoint
    """
    record = await get_content_from_db(asession, content_id)

    if not record:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_id}` not found"
        )
    await delete_content_from_db(asession, content_id)


@router.get("/{content_id}", response_model=ContentRetrieve)
async def retrieve_content_by_id(
    content_id: int,
    readonly_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_readonly_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve:
    """
    Retrieve content by id endpoint
    """

    record = await get_content_from_db(asession, content_id)

    if not record:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_id}` not found"
        )

    return _convert_record_to_schema(record)


def _convert_record_to_schema(record: ContentDB) -> ContentRetrieve:
    """
    Convert db_models.ContentDB models to ContentRetrieve schema
    """
    content_retrieve = ContentRetrieve(
        content_id=record.content_id,
        content_title=record.content_title,
        content_text=record.content_text,
        content_embedding=record.content_embedding,
        content_language=record.content_language,
        content_metadata=record.content_metadata,
        created_datetime_utc=record.created_datetime_utc,
        updated_datetime_utc=record.updated_datetime_utc,
    )

    return content_retrieve


def _create_payload_for_qdrant_upsert(
    content_title: str, content_text: str, metadata: dict
) -> QdrantPayload:
    """
    Create payload for qdrant upsert
    """
    payload_dict = metadata.copy()
    payload_dict["content_title"] = content_title
    payload_dict["content_text"] = content_text
    payload = QdrantPayload(**payload_dict)
    payload.updated_datetime_utc = datetime.utcnow()

    return payload


def _upsert_content_to_qdrant(
    content_id: UUID,
    content: ContentCreate,
    payload: QdrantPayload,
    qdrant_client: QdrantClient,
) -> ContentRetrieve:
    """Add content to qdrant collection"""

    text_to_embed = content.content_title + "\n" + content.content_text
    content_embedding = embedding(EMBEDDING_MODEL, text_to_embed).data[0]["embedding"]

    qdrant_client.upsert(
        collection_name=QDRANT_COLLECTION_NAME,
        points=[
            PointStruct(
                id=str(content_id),
                vector=content_embedding,
                payload=payload.model_dump(),
            )
        ],
    )

    return ContentRetrieve(
        **content.model_dump(),
        content_id=content_id,
        created_datetime_utc=payload.created_datetime_utc,
        updated_datetime_utc=payload.updated_datetime_utc,
    )
