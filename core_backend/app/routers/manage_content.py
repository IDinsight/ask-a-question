import uuid
from datetime import datetime
from typing import List, Union
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from litellm import embedding
from qdrant_client import QdrantClient
from qdrant_client.models import PointIdsList, PointStruct, Record

from ..configs.app_config import EMBEDDING_MODEL, QDRANT_COLLECTION_NAME
from ..db.vector_db import get_qdrant_client
from ..schemas import ContentCreate, ContentRetrieve
from ..utils import setup_logger

router = APIRouter(prefix="/content")
logger = setup_logger()


@router.post("/create", response_model=ContentRetrieve)
async def create_content(
    content: ContentCreate, qdrant_client: QdrantClient = Depends(get_qdrant_client)
) -> ContentRetrieve:
    """
    Create content endpoint. Calls embedding model to get content embedding and
    upserts it to Qdrant collection.
    """

    payload = dict(content.content_metadata)
    payload["created_datetime_utc"] = datetime.utcnow()
    payload["updated_datetime_utc"] = datetime.utcnow()
    payload["content_text"] = content.content_text

    content_id = uuid.uuid4()

    return _add_content_to_qdrant(
        content_id=content_id,
        content=content,
        payload=payload,
        qdrant_client=qdrant_client,
    )


@router.put("/{content_id}/edit", response_model=ContentRetrieve)
async def edit_content(
    content_id: str,
    content: ContentCreate,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
) -> ContentRetrieve:
    """
    Edit content endpoint
    """

    # retrive old content
    old_content = qdrant_client.retrieve(QDRANT_COLLECTION_NAME, ids=[content_id])
    if len(old_content) == 0:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_id}` not found"
        )

    payload = old_content[0].payload or {}
    payload.update(content.content_metadata)
    payload["updated_datetime_utc"] = datetime.utcnow()
    payload["content_text"] = content.content_text

    return _add_content_to_qdrant(
        content_id=content_id,
        content=content,
        payload=payload,
        qdrant_client=qdrant_client,
    )


@router.get("/list", response_model=list[ContentRetrieve])
async def retrieve_content(
    skip: int = 0,
    limit: int = 10,
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

    contents = [_record_to_schema(c) for c in records]
    return contents


@router.delete("/{content_id}/delete")
async def delete_content(
    content_id: str, qdrant_client: QdrantClient = Depends(get_qdrant_client)
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
    content_id: str, qdrant_client: QdrantClient = Depends(get_qdrant_client)
) -> ContentRetrieve:
    """
    Retrieve content by id endpoint
    """

    record = qdrant_client.retrieve(QDRANT_COLLECTION_NAME, ids=[content_id])

    if len(record) == 0:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_id}` not found"
        )

    return _record_to_schema(record[0])


def _add_content_to_qdrant(
    content_id: Union[str, UUID],
    content: ContentCreate,
    payload: dict,
    qdrant_client: QdrantClient,
) -> ContentRetrieve:
    """Add content to qdrant collection."""
    content_embedding = (
        embedding(EMBEDDING_MODEL, content.content_text).data[0].embedding
    )

    qdrant_client.upsert(
        collection_name=QDRANT_COLLECTION_NAME,
        points=[
            PointStruct(
                id=str(content_id),
                vector=content_embedding,
                payload=payload,
            )
        ],
    )

    if not isinstance(content_id, UUID):
        content_id = UUID(content_id)

    return ContentRetrieve(
        **content.model_dump(),
        content_id=content_id,
        created_datetime_utc=payload["created_datetime_utc"],
        updated_datetime_utc=payload["updated_datetime_utc"],
    )


def _record_to_schema(record: Record) -> ContentRetrieve:
    """
    Convert qdrant_client.models.Record to ContentRetrieve schema
    """
    content_metadata = record.payload or {}
    created_datetime = content_metadata.pop("created_datetime_utc")
    updated_datetime = content_metadata.pop("updated_datetime_utc")
    content_text = content_metadata.pop("content_text")

    return ContentRetrieve(
        content_text=content_text,
        content_metadata=content_metadata,
        content_id=UUID(str(record.id)),
        created_datetime_utc=created_datetime,
        updated_datetime_utc=updated_datetime,
    )
