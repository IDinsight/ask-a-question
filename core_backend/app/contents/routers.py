from typing import Annotated, List, Optional, Union

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_fullaccess_user, get_current_readonly_user
from .models import (
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
from ..database import get_async_session
from ..auth.schemas import AuthenticatedUser
from .schemas import (
    ContentTextRetrieve,
    ContentSummary,
    ContentTextCreate,
)
from ..utils import setup_logger

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
