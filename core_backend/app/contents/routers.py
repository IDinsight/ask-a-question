from typing import Annotated, List

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_async_session
from ..tags.models import validate_tags
from ..users.models import UserDB
from ..utils import setup_logger
from .models import (
    ContentDB,
    delete_content_from_db,
    get_content_from_db,
    get_list_of_content_from_db,
    save_content_to_db,
    update_content_in_db,
)
from .schemas import ContentCreate, ContentRetrieve

router = APIRouter(prefix="/content", tags=["Content Management"])
logger = setup_logger()


@router.post("/", response_model=ContentRetrieve)
async def create_content(
    content: ContentCreate,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve | None:
    """
    Create content endpoint. Calls embedding model to get content embedding and
    inserts it to PG database
    """
    is_tag_valid, content_tags = await validate_tags(
        user_db.user_id, content.content_tags, asession
    )
    if not is_tag_valid:
        raise HTTPException(status_code=400, detail=f"Invalid tags id: {content_tags}")
    content.content_tags = content_tags
    content_db = await save_content_to_db(
        user_id=user_db.user_id,
        content=content,
        asession=asession,
    )
    return _convert_record_to_schema(content_db)


@router.put("/{content_id}", response_model=ContentRetrieve)
async def edit_content(
    content_id: int,
    content: ContentCreate,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve:
    """
    Edit content endpoint
    """

    old_content = await get_content_from_db(
        user_id=user_db.user_id,
        content_id=content_id,
        asession=asession,
    )

    if not old_content:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_id}` not found"
        )

    is_tag_valid, content_tags = await validate_tags(
        user_db.user_id, content.content_tags, asession
    )
    if not is_tag_valid:
        raise HTTPException(status_code=400, detail=f"Invalid tags id: {content_tags}")
    content.content_tags = content_tags
    updated_content = await update_content_in_db(
        user_id=user_db.user_id,
        content_id=content_id,
        content=content,
        asession=asession,
    )

    return _convert_record_to_schema(updated_content)


@router.get("/", response_model=list[ContentRetrieve])
async def retrieve_content(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 50,
    asession: AsyncSession = Depends(get_async_session),
) -> List[ContentRetrieve]:
    """
    Retrieve all content endpoint
    """

    records = await get_list_of_content_from_db(
        user_id=user_db.user_id,
        offset=skip,
        limit=limit,
        asession=asession,
    )
    contents = [_convert_record_to_schema(c) for c in records]
    return contents


@router.delete("/{content_id}")
async def delete_content(
    content_id: int,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Delete content endpoint
    """

    record = await get_content_from_db(
        user_id=user_db.user_id,
        content_id=content_id,
        asession=asession,
    )

    if not record:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_id}` not found"
        )
    await delete_content_from_db(
        user_id=user_db.user_id,
        content_id=content_id,
        asession=asession,
    )


@router.get("/{content_id}", response_model=ContentRetrieve)
async def retrieve_content_by_id(
    content_id: int,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve:
    """
    Retrieve content by id endpoint
    """

    record = await get_content_from_db(
        user_id=user_db.user_id,
        content_id=content_id,
        asession=asession,
    )

    if not record:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_id}` not found"
        )

    return _convert_record_to_schema(record)


def _convert_record_to_schema(record: ContentDB) -> ContentRetrieve:
    """
    Convert models.ContentDB models to ContentRetrieve schema
    """

    content_retrieve = ContentRetrieve(
        content_id=record.content_id,
        user_id=record.user_id,
        content_title=record.content_title,
        content_text=record.content_text,
        content_language=record.content_language,
        content_tags=[tag.tag_id for tag in record.content_tags],
        positive_votes=record.positive_votes,
        negative_votes=record.negative_votes,
        content_metadata=record.content_metadata,
        created_datetime_utc=record.created_datetime_utc,
        updated_datetime_utc=record.updated_datetime_utc,
    )

    return content_retrieve
