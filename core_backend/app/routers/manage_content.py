from typing import Annotated, List, Optional, Union

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_fullaccess_user, get_current_readonly_user
from ..db.db_models import (
    ContentTextDB,
    delete_content_text_from_db,
    get_all_languages_version_of_content,
    get_content_from_content_id_and_language,
    get_content_from_db,
    get_language_from_db,
    get_list_of_content_from_db,
    get_summary_of_content_from_db,
    is_content_language_combination_unique,
    save_content_to_db,
    update_content_in_db,
)
from ..db.engine import get_async_session
from ..schemas import (
    AuthenticatedUser,
    ContentRetrieve,
    ContentSummary,
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
    is_valid, reason = await validate_create_content(
        content=content,
        asession=asession,
    )
    if is_valid:
        content_db = await save_content_to_db(content, asession)
        return _convert_record_to_schema(content_db)
    else:
        raise HTTPException(
            status_code=400,
            detail=reason,
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
            status_code=404, detail=f"Content text id `{content_text_id}` not found"
        )

    is_valid, reason = await validate_edit_content(
        content=content,
        asession=asession,
        old_content=old_content,
    )
    if is_valid:
        updated_content = await update_content_in_db(
            content_text_id,
            old_content,
            content,
            asession,
        )

        return _convert_record_to_schema(updated_content)
    else:
        raise HTTPException(
            status_code=400,
            detail=reason,
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


@router.get("/summary", response_model=list[ContentSummary])
async def retrieve_content_summary(
    readonly_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_readonly_user)
    ],
    language: int,
    skip: int = 0,
    limit: int = 50,
    asession: AsyncSession = Depends(get_async_session),
) -> List[ContentSummary]:
    """
    Retrieve all content endpoint
    """
    records = await get_summary_of_content_from_db(
        language_id=language, offset=skip, limit=limit, asession=asession
    )
    contents = [_convert_summary_to_schema(c) for c in records]
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
            status_code=404, detail=f"Content text id `{content_text_id}` not found"
        )

    await delete_content_text_from_db(content_text_id, record.content_id, asession)


@router.get(
    "/{content_text_id}", response_model=Union[ContentRetrieve, List[ContentRetrieve]]
)
async def retrieve_content_by_id(
    content_text_id: int,
    readonly_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_readonly_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
    language: Optional[str] = None,
) -> Union[ContentRetrieve, List[ContentRetrieve]]:
    """
    Retrieve content by id endpoint
    """

    content = await get_content_from_db(content_text_id, asession)

    if not content:
        raise HTTPException(
            status_code=404, detail=f"Content text id `{content_text_id}` not found"
        )

    if language:
        record = await get_content_from_content_id_and_language(
            content.content_id, int(language), asession
        )
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"""Content `{content_text_id}`
                with language id `{language}` not found""",
            )
        return _convert_record_to_schema(record)
    else:
        records = await get_all_languages_version_of_content(
            content.content_id, asession
        )
        return [_convert_record_to_schema(record) for record in records]


async def validate_create_content(
    content: ContentTextCreate,
    asession: AsyncSession,
) -> tuple[bool, Optional[str]]:
    """
    Make sure the content and language is valid before saving content_text to db.
    """
    if content.content_id is not None:
        contents = await get_all_languages_version_of_content(
            content.content_id, asession=asession
        )
        if len(contents) < 1:
            return (False, f"Content id `{content.content_id}` does not exist")

    language = await get_language_from_db(content.language_id, asession)
    if not language:
        return (False, f"Language id `{content.language_id}` does not exist")

    if not (
        await is_content_language_combination_unique(
            content.content_id, content.language_id, asession
        )
    ):
        return (False, "Content and language combination already exists")

    return (True, None)


async def validate_edit_content(
    content: ContentTextCreate, old_content: ContentTextDB, asession: AsyncSession
) -> tuple[bool, Optional[str]]:
    """
    Validate content and language before editing content text.
    """
    if not content.content_id:
        content.content_id = old_content.content_id
    else:
        contents = await get_all_languages_version_of_content(
            content.content_id, asession=asession
        )
        if len(contents) < 1:
            return (False, f"Content id `{content.content_id}` does not exist")

    language = await get_language_from_db(content.language_id, asession)
    if not language:
        return (False, f"Language id `{content.language_id}` does not exist")

    is_language_updated = old_content.language_id != content.language_id

    if is_language_updated and not (
        await is_content_language_combination_unique(
            content.content_id, content.language_id, asession
        )
    ):
        return (False, "Content and language combination already exists")

    return (True, None)


def _convert_record_to_schema(record: ContentTextDB) -> ContentRetrieve:
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


def _convert_summary_to_schema(record: Row) -> ContentSummary:
    """
    Convert db_models.ContentDB models to ContentRetrieve schema
    """
    content_retrieve = ContentSummary(
        content_text_id=record[0],
        content_id=record[1],
        content_title=record[2],
        created_datetime_utc=record[3],
        updated_datetime_utc=record[4],
        languages=record[5],
    )

    return content_retrieve
