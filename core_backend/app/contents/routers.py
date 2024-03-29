from typing import Annotated, List, Optional, Union

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_fullaccess_user, get_current_readonly_user
from ..auth.schemas import AuthenticatedUser
from ..database import get_async_session
from ..languages.models import get_language_from_db, get_language_from_language_name_db
from ..utils import setup_logger
from .models import (
    ContentTextDB,
    delete_content_from_db,
    get_all_languages_version_of_content,
    get_content_from_content_id_and_language,
    get_content_from_db,
    get_landing_view_of_content_from_db,
    get_list_of_content_from_db,
    is_content_language_combination_unique,
    save_content_to_db,
    update_content_in_db,
)
from .schemas import (
    ContentLanding,
    ContentTextCreate,
    ContentTextRetrieve,
)

router = APIRouter(prefix="/content")
logger = setup_logger()


@router.post("/", response_model=ContentTextRetrieve)
async def create_content(
    content: ContentTextCreate,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> ContentTextRetrieve | None:
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


@router.put("/{content_id}", response_model=ContentTextRetrieve)
async def edit_content(
    content_id: int,
    content: ContentTextCreate,
    language_id: int,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> ContentTextRetrieve:
    """
    Edit content endpoint
    """
    language_db = await get_language_from_db(language_id, asession)
    if not language_db:
        raise HTTPException(
            status_code=404, detail=f"Language `{language_id}` not found"
        )

    old_content = await get_content_from_content_id_and_language(
        content_id,
        language_db.language_id,
        asession,
    )

    is_valid, reason = await validate_edit_content(
        content=content, old_content=old_content, asession=asession
    )
    if is_valid:
        if old_content:
            updated_content = await update_content_in_db(
                old_content,
                content,
                asession,
            )
        else:
            updated_content = await save_content_to_db(content, asession)

        return _convert_record_to_schema(updated_content)
    else:
        raise HTTPException(
            status_code=400,
            detail=reason,
        )


@router.get("/", response_model=list[ContentTextRetrieve])
async def retrieve_content(
    readonly_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_readonly_user)
    ],
    skip: int = 0,
    limit: int = 50,
    asession: AsyncSession = Depends(get_async_session),
) -> List[ContentTextRetrieve]:
    """
    Retrieve all content endpoint
    """
    records = await get_list_of_content_from_db(
        offset=skip, limit=limit, asession=asession
    )
    contents = [_convert_record_to_schema(c) for c in records]
    return contents


@router.get("/landing", response_model=list[ContentLanding])
async def retrieve_content_landing(
    readonly_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_readonly_user)
    ],
    language: str,
    skip: int = 0,
    limit: int = 50,
    asession: AsyncSession = Depends(get_async_session),
) -> List[ContentLanding]:
    """
    Retrieve landing view of all contents endpoint
    """
    language_db = await get_language_from_language_name_db(language, asession)
    if not language_db:
        raise HTTPException(status_code=404, detail=f"Language `{language}` not found")
    records = await get_landing_view_of_content_from_db(
        language_id=language_db.language_id, offset=skip, limit=limit, asession=asession
    )
    contents = [_convert_summary_to_schema(c) for c in records]
    return contents


@router.delete("/{content_id}")
async def delete_content(
    content_id: int,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
    language: Optional[str] = None,
) -> None:
    """
    Delete content endpoint.
    If no language is provided, all languages versions of the content will be deleted
    """
    if language:
        language_db = await get_language_from_language_name_db(
            language.upper(), asession
        )
        if not language_db:
            raise HTTPException(
                status_code=404,
                detail=f"Language `{language}` not found",
            )
        record = await get_content_from_content_id_and_language(
            content_id, language_db.language_id, asession
        )
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"""Content `{content_id}`
                with language name `{language}` not found""",
            )
        await delete_content_from_db(
            content_id,
            asession,
            language_db.language_id,
        )
    else:
        records = await get_all_languages_version_of_content(content_id, asession)
        if len(records) < 1:
            raise HTTPException(
                status_code=404,
                detail=f"Content `{content_id}` not found",
            )
        await delete_content_from_db(content_id, asession)


@router.get(
    "/{content_id}",
    response_model=Union[ContentTextRetrieve, List[ContentTextRetrieve]],
)
async def retrieve_content_by_id(
    content_id: int,
    readonly_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_readonly_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
    language: Optional[str] = None,
) -> Union[ContentTextRetrieve, List[ContentTextRetrieve]]:
    """
    Retrieve content by id endpoint
    """

    if language:
        language_db = await get_language_from_language_name_db(
            language.upper(), asession
        )
        if not language_db:
            raise HTTPException(
                status_code=404,
                detail=f"Language `{language}` not found",
            )
        record = await get_content_from_content_id_and_language(
            content_id, language_db.language_id, asession
        )
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"""Content `{content_id}`
                with language name `{language}` not found""",
            )
        return _convert_record_to_schema(record)
    else:
        records = await get_all_languages_version_of_content(content_id, asession)
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
    content: ContentTextCreate,
    asession: AsyncSession,
    old_content: Optional[ContentTextDB] = None,
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

    if old_content:
        is_language_updated = old_content.language_id != content.language_id

        if is_language_updated and not (
            await is_content_language_combination_unique(
                content.content_id, content.language_id, asession
            )
        ):
            return (False, "Content and language combination already exists")

    return (True, None)


def _convert_record_to_schema(record: ContentTextDB) -> ContentTextRetrieve:
    """
    Convert db_models.ContentDB models to ContentTextRetrieve schema
    """
    content_retrieve = ContentTextRetrieve(
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


def _convert_summary_to_schema(record: Row) -> ContentLanding:
    """
    Convert db_models.ContentDB models to ContentTextRetrieve schema
    """
    content_retrieve = ContentLanding(
        content_text_id=record[0],
        content_id=record[1],
        content_title=record[2],
        content_text=record[3],
        created_datetime_utc=record[4],
        updated_datetime_utc=record[5],
        languages=record[6],
    )

    return content_retrieve
