from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from app.db.engine import get_async_session

from datetime import datetime
from typing import List
from app.db.db_models import Content
from app.schemas import ContentCreate, ContentRetrieve
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter(prefix="/content")


@router.post("/create", response_model=ContentRetrieve)
async def create_content(
    content: ContentCreate, asession: AsyncSession = Depends(get_async_session)
) -> ContentRetrieve:
    """
    Create content endpoint
    """

    content_db = Content(
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
        **content.dict(),
    )

    asession.add(content_db)
    await asession.commit()
    await asession.refresh(content_db)

    return ContentRetrieve.from_orm(content_db)


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

    return content_db


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

    return content


@router.get("/retrieve", response_model=list[ContentRetrieve])
async def retrieve_content(
    skip: int = 0, limit: int = 10, asession: AsyncSession = Depends(get_async_session)
) -> List[ContentRetrieve]:
    """
    Retrieve all content endpoint
    """
    statement = select(Content).offset(skip).limit(limit)
    contents = (await asession.execute(statement)).all()
    contents = [content[0] for content in contents]
    return contents
