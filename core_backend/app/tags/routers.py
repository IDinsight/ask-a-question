from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_async_session
from ..users.models import UserDB
from ..utils import setup_logger
from .models import (
    TagDB,
    delete_tag_from_db,
    get_list_of_tag_from_db,
    get_tag_from_db,
    is_tag_name_unique,
    save_tag_to_db,
    update_tag_in_db,
)
from .schemas import TagCreate, TagRetrieve

TAG_METADATA = {
    "name": "Question-answering content tags management",
    "description": "Manage tags for content used for question answering",
}

router = APIRouter(prefix="/tag", tags=[TAG_METADATA["name"]])
logger = setup_logger()


@router.post("/", response_model=TagRetrieve)
async def create_tag(
    tag: TagCreate,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> TagRetrieve | None:
    """
    Create tag endpoint. Calls embedding model to upsert tag to database.
    """
    tag.tag_name = tag.tag_name.upper()
    if not await is_tag_name_unique(user_db.user_id, tag.tag_name, asession):
        raise HTTPException(
            status_code=400, detail=f"Tag name `{tag.tag_name}` already exists"
        )
    tag_db = await save_tag_to_db(user_db.user_id, tag, asession)
    return _convert_record_to_schema(tag_db)


@router.put("/{tag_id}", response_model=TagRetrieve)
async def edit_tag(
    tag_id: int,
    tag: TagCreate,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> TagRetrieve:
    """
    Edit tag endpoint
    """
    tag.tag_name = tag.tag_name.upper()
    old_tag = await get_tag_from_db(
        user_db.user_id,
        tag_id,
        asession,
    )

    if not old_tag:
        raise HTTPException(status_code=404, detail=f"Tag id `{tag_id}` not found")
    if (tag.tag_name != old_tag.tag_name) and not (
        await is_tag_name_unique(user_db.user_id, tag.tag_name, asession)
    ):
        raise HTTPException(
            status_code=400, detail=f"Tag name `{tag.tag_name}` already exists"
        )
    updated_tag = await update_tag_in_db(
        user_db.user_id,
        tag_id,
        tag,
        asession,
    )

    return _convert_record_to_schema(updated_tag)


@router.get("/", response_model=list[TagRetrieve])
async def retrieve_tag(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    skip: int = 0,
    limit: Optional[int] = None,
    asession: AsyncSession = Depends(get_async_session),
) -> List[TagRetrieve]:
    """
    Retrieve all tag endpoint
    """
    records = await get_list_of_tag_from_db(
        user_db.user_id, offset=skip, limit=limit, asession=asession
    )
    tags = [_convert_record_to_schema(c) for c in records]
    return tags


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Delete tag endpoint
    """
    record = await get_tag_from_db(
        user_db.user_id,
        tag_id,
        asession,
    )

    if not record:
        raise HTTPException(status_code=404, detail=f"Tag id `{tag_id}` not found")
    await delete_tag_from_db(user_db.user_id, tag_id, asession)


@router.get("/{tag_id}", response_model=TagRetrieve)
async def retrieve_tag_by_id(
    tag_id: int,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> TagRetrieve:
    """
    Retrieve tag by id endpoint
    """

    record = await get_tag_from_db(user_db.user_id, tag_id, asession)

    if not record:
        raise HTTPException(status_code=404, detail=f"Tag id `{tag_id}` not found")

    return _convert_record_to_schema(record)


def _convert_record_to_schema(record: TagDB) -> TagRetrieve:
    """
    Convert  models.TagDB models to TagRetrieve schema
    """
    tag_retrieve = TagRetrieve(
        tag_id=record.tag_id,
        tag_name=record.tag_name,
        user_id=record.user_id,
        created_datetime_utc=record.created_datetime_utc,
        updated_datetime_utc=record.updated_datetime_utc,
    )

    return tag_retrieve
