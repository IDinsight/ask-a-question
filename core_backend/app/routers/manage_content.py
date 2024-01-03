import uuid
from datetime import datetime
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from litellm import embedding
from pydantic import BaseModel, ConfigDict, Field
from qdrant_client import QdrantClient
from qdrant_client.models import PointIdsList, PointStruct, Record

from ..auth import get_current_fullaccess_user, get_current_readonly_user
from ..configs.app_config import EMBEDDING_MODEL, QDRANT_COLLECTION_NAME
from ..db.vector_db import get_qdrant_client
from ..schemas import AuthenticatedUser, ContentCreate, ContentRetrieve
from ..utils import setup_logger

router = APIRouter(prefix="/content")
logger = setup_logger()


class QdrantPayload(BaseModel):
    """Content payload for qdrant"""

    content_title: str = Field(default="")
    content_text: str
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
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
) -> ContentRetrieve:
    """
    Create content endpoint. Calls embedding model to get content embedding and
    upserts it to Qdrant collection.
    """

    payload = _create_payload_for_qdrant_upsert(
        content.content_title, content.content_text, content.content_metadata
    )

    content_id = uuid.uuid4()

    return _upsert_content_to_qdrant(
        content_id=content_id,
        content=content,
        payload=payload,
        qdrant_client=qdrant_client,
    )


@router.put("/{content_id}/edit", response_model=ContentRetrieve)
async def edit_content(
    content_id: str,
    content: ContentCreate,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
) -> ContentRetrieve:
    """
    Edit content endpoint
    """
    old_content = qdrant_client.retrieve(QDRANT_COLLECTION_NAME, ids=[content_id])

    if len(old_content) == 0:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_id}` not found"
        )

    payload = _create_payload_for_qdrant_upsert(
        content_title=content.content_title,
        content_text=content.content_text,
        metadata=old_content[0].payload or {},
    )
    payload = payload.model_copy(update=content.content_metadata)

    return _upsert_content_to_qdrant(
        content_id=UUID(content_id),
        content=content,
        payload=payload,
        qdrant_client=qdrant_client,
    )


@router.get("/list", response_model=list[ContentRetrieve])
async def retrieve_content(
    readonly_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_readonly_user)
    ],
    skip: int = 0,
    limit: int = 50,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
) -> List[ContentRetrieve]:
    """
    Retrieve all content endpoint
    """
    records, _ = qdrant_client.scroll(
        collection_name=QDRANT_COLLECTION_NAME,
        limit=limit,
        offset=skip,
        with_payload=True,
        with_vectors=False,
    )

    contents = [_convert_record_to_schema(c) for c in records]
    return contents


@router.delete("/{content_id}/delete")
async def delete_content(
    content_id: str,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
) -> None:
    """
    Delete content endpoint
    """
    record = qdrant_client.retrieve(QDRANT_COLLECTION_NAME, ids=[content_id])

    if len(record) == 0:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_id}` not found"
        )

    qdrant_client.delete(
        collection_name=QDRANT_COLLECTION_NAME,
        points_selector=PointIdsList(points=[content_id]),
    )


@router.get("/{content_id}", response_model=ContentRetrieve)
async def retrieve_content_by_id(
    content_id: str,
    readonly_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_readonly_user)
    ],
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
) -> ContentRetrieve:
    """
    Retrieve content by id endpoint
    """

    record = qdrant_client.retrieve(QDRANT_COLLECTION_NAME, ids=[content_id])

    if len(record) == 0:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_id}` not found"
        )

    return _convert_record_to_schema(record[0])


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
    content_embedding = embedding(EMBEDDING_MODEL, text_to_embed).data[0][
        "embedding"
    ]

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


def _convert_record_to_schema(record: Record) -> ContentRetrieve:
    """
    Convert qdrant_client.models.Record to ContentRetrieve schema
    """
    content_metadata = record.payload or {}
    created_datetime = content_metadata.pop("created_datetime_utc")
    updated_datetime = content_metadata.pop("updated_datetime_utc")
    content_title = content_metadata.pop("content_title")
    content_text = content_metadata.pop("content_text")

    return ContentRetrieve(
        content_title=content_title,
        content_text=content_text,
        content_metadata=content_metadata,
        content_id=UUID(str(record.id)),
        created_datetime_utc=created_datetime,
        updated_datetime_utc=updated_datetime,
    )
