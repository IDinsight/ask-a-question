import uuid

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from app.db.engine import get_async_session

from datetime import datetime
from typing import List
from app.db.db_models import Content
from app.schemas import ContentCreate, ContentRetrieve
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.vector_db import get_qdrant_client
from app.configs.app_config import QDRANT_COLLECTION_NAME, EMBEDDING_MODEL
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from litellm import embedding

router = APIRouter(prefix="/content")


@router.post("/create", response_model=ContentRetrieve)
async def create_content(
    content: ContentCreate, qdrant_client: QdrantClient = Depends(get_qdrant_client)
) -> ContentRetrieve:
    """
    Create content endpoint. Calls embedding model to get content embedding and
    upserts it to Qdrant collection.
    """

    content_embedding = (
        embedding(EMBEDDING_MODEL, content.content_text).data[0].embedding
    )
    point_id = str(uuid.uuid4())

    payload = dict(content.content_metadata)
    payload["created_datetime_utc"] = datetime.utcnow()
    payload["updated_datetime_utc"] = datetime.utcnow()

    qdrant_client.upsert(
        collection_name=QDRANT_COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=content_embedding,
                payload=payload,
            )
        ],
    )

    return ContentRetrieve(
        **content.model_dump(),
        content_id=point_id,
        created_datetime_utc=payload["created_datetime_utc"],
        updated_datetime_utc=payload["updated_datetime_utc"],
    )


@router.post("/edit/{content_id}", response_model=ContentRetrieve)
async def edit_content(
    content_id: int,
    content: ContentCreate,
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve:
    """
    Edit content endpoint
    """

    content_db = await asession.get(Content, content_id)

    if content_db is None:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_id}` not found"
        )

    content_db.updated_datetime_utc = datetime.utcnow()

    for key, value in content.dict().items():
        setattr(content_db, key, value)

    await asession.commit()
    await asession.refresh(content_db)

    return ContentRetrieve.model_validate(content_db)


@router.get("/retrieve/{content_id}", response_model=ContentRetrieve)
async def retrieve_content_by_id(
    content_id: int, asession: AsyncSession = Depends(get_async_session)
) -> ContentRetrieve:
    """
    Retrieve content by id endpoint
    """
    content = await asession.get(Content, content_id)

    if content is None:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_id}` not found"
        )

    return ContentRetrieve.model_validate(content)


@router.get("/retrieve", response_model=list[ContentRetrieve])
async def retrieve_content(
    skip: int = 0, limit: int = 10, asession: AsyncSession = Depends(get_async_session)
) -> List[ContentRetrieve]:
    """
    Retrieve all content endpoint
    """
    statement = select(Content).offset(skip).limit(limit)
    contents_db = (await asession.execute(statement)).all()
    contents = [ContentRetrieve.model_validate(c[0]) for c in contents_db]
    return contents
