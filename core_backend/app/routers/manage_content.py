from typing import Annotated, List

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_fullaccess_user, get_current_readonly_user
from ..db.db_models import (
    ContentDB,
    delete_content_from_db,
    get_all_languages_version_of_content,
    get_content_from_db,
    get_language_from_db,
    get_list_of_content_from_db,
    is_content_language_combination_unique,
    save_content_to_db,
    update_content_in_db,
)
from ..db.engine import get_async_session
from ..schemas import (
    AuthenticatedUser,
    ContentRetrieve,
    ContentTextCreate,
)
from ..utils import setup_logger

router = APIRouter(prefix="/content")
logger = setup_logger()


@router.post("/create", response_model=ContentRetrieve)
async def create_content(
    content: ContentTextCreate,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve | None:
    """
    Create content endpoint. Calls embedding model to get content embedding and
    upserts it to PG database
    """
    if await is_content_and_language_valid(content, asession):
        content_db = await save_content_to_db(content, asession)
        return _convert_record_to_schema(content_db)
    else:
        raise HTTPException(
            status_code=400,
            detail="Content could not be added",
        )


@router.put("/{content_text_id}/edit", response_model=ContentRetrieve)
async def edit_content(
    content_text_id: int,
    content: ContentTextCreate,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve:
    """
    Edit content endpoint
    """
    old_content = await get_content_from_db(
        content_text_id,
        asession,
    )

    if not old_content:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_text_id}` not found"
        )
    is_updated_language = old_content.language_id != content.language_id

    if await is_content_and_language_valid(
        content, asession, True, is_updated_language
    ):
        updated_content = await update_content_in_db(
            content_text_id,
            content,
            asession,
        )

        return _convert_record_to_schema(updated_content)
    else:
        raise HTTPException(
            status_code=400,
            detail="Content could not be updated",
        )


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
    records = await get_list_of_content_from_db(
        offset=skip, limit=limit, asession=asession
    )
    contents = [_convert_record_to_schema(c) for c in records]
    return contents


@router.delete("/{content_text_id}/delete")
async def delete_content(
    content_text_id: int,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Delete content endpoint
    """
    record = await get_content_from_db(
        content_text_id,
        asession,
    )

    if not record:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_text_id}` not found"
        )
    await delete_content_from_db(content_text_id, record.content_id, asession)


@router.get("/{content_text_id}", response_model=ContentRetrieve)
async def retrieve_content_by_id(
    content_text_id: int,
    readonly_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_readonly_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve:
    """
    Retrieve content by id endpoint
    """

    record = await get_content_from_db(content_text_id, asession)

    if not record:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_text_id}` not found"
        )

    return _convert_record_to_schema(record)


@router.get("/{content_text_id}/list", response_model=list[ContentRetrieve])
async def retrieve_all_languages_versions(
    content_text_id: int,
    readonly_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_readonly_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> List[ContentRetrieve]:
    """
    Retrieve content by id endpoint
    """
    content = await get_content_from_db(content_text_id, asession)
    if not content:
        raise HTTPException(
            status_code=404, detail=f"Content id `{content_text_id}` not found"
        )
    records = await get_all_languages_version_of_content(content.content_id, asession)

    return [_convert_record_to_schema(record) for record in records]


async def is_content_and_language_valid(
    content: ContentTextCreate,
    asession: AsyncSession,
    is_edit: bool = False,
    is_updated_language: bool = True,
) -> bool:
    contents = await get_all_languages_version_of_content(
        content.content_id, asession=asession
    )
    if len(contents) < 1:
        if is_edit or content.content_id != 0:
            raise HTTPException(
                status_code=400,
                detail=f"Content id `{content.content_id}` does not exist",
            )

    language = await get_language_from_db(content.language_id, asession)
    if not language:
        raise HTTPException(
            status_code=400,
            detail=f"Language id `{content.language_id}` does not exist",
        )
    if is_updated_language and not (
        await is_content_language_combination_unique(
            content.content_id, content.language_id, asession
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Content and language combination already exists",
        )

    return True


def _convert_record_to_schema(record: ContentDB) -> ContentRetrieve:
    """
    Convert db_models.ContentDB models to ContentRetrieve schema
    """
    content_retrieve = ContentRetrieve(
        content_text_id=record.content_text_id,
        content_title=record.content_title,
        content_text=record.content_text,
        content_id=record.content_id,
        language_id=record.language_id,
        content_metadata=record.content_metadata,
        created_datetime_utc=record.created_datetime_utc,
        updated_datetime_utc=record.updated_datetime_utc,
    )

    return content_retrieve
