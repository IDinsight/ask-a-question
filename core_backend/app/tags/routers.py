from typing import Annotated, List

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..auth.schemas import AuthenticatedUser
from ..database import get_async_session
from ..utils import setup_logger
from .models import (
    TagDB,
    delete_tag_from_db,
    get_tag_from_db,
    get_list_of_tag_from_db,
    save_tag_to_db,
    update_tag_in_db,
)
from .schemas import TagCreate, TagRetrieve

router = APIRouter(prefix="/tag", tags=["Tag Management"])
logger = setup_logger()


@router.post("/", response_model=TagRetrieve)
async def create_tag(
    tag: TagCreate,
    full_access_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> TagRetrieve | None:
    """
    Create tag endpoint. Calls embedding model to upsert tag to PG database
    """

    tag_db = await save_tag_to_db(tag, asession)
    return _convert_record_to_schema(tag_db)


@router.put("/{tag_id}", response_model=TagRetrieve)
async def edit_tag(
    tag_id: int,
    tag: TagCreate,
    full_access_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> TagRetrieve:
    """
    Edit tag endpoint
    """
    old_tag = await get_tag_from_db(
        tag_id,
        asession,
    )

    if not old_tag:
        raise HTTPException(status_code=404, detail=f"Tag id `{tag_id}` not found")
    updated_tag = await update_tag_in_db(
        tag_id,
        tag,
        asession,
    )

    return _convert_record_to_schema(updated_tag)


@router.get("/", response_model=list[TagRetrieve])
async def retrieve_tag(
    readonly_access_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 50,
    asession: AsyncSession = Depends(get_async_session),
) -> List[TagRetrieve]:
    """
    Retrieve all tag endpoint
    """
    records = await get_list_of_tag_from_db(offset=skip, limit=limit, asession=asession)
    tags = [_convert_record_to_schema(c) for c in records]
    return tags


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    full_access_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Delete tag endpoint
    """
    record = await get_tag_from_db(
        tag_id,
        asession,
    )

    if not record:
        raise HTTPException(status_code=404, detail=f"Tag id `{tag_id}` not found")
    await delete_tag_from_db(tag_id, asession)


@router.get("/{tag_id}", response_model=TagRetrieve)
async def retrieve_tag_by_id(
    tag_id: int,
    readonly_access_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> TagRetrieve:
    """
    Retrieve tag by id endpoint
    """

    record = await get_tag_from_db(tag_id, asession)

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
        created_datetime_utc=record.created_datetime_utc,
        updated_datetime_utc=record.updated_datetime_utc,
    )

    return tag_retrieve
