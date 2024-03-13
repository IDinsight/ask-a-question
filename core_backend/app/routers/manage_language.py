from typing import Annotated, List

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_fullaccess_user, get_current_readonly_user
from ..db.db_models import (
    LanguageDB,
    delete_language_from_db,
    get_default_language_from_db,
    get_language_from_db,
    get_list_of_languages_from_db,
    is_language_name_unique,
    save_language_to_db,
    update_language_in_db,
)
from ..db.engine import get_async_session
from ..schemas import AuthenticatedUser, LanguageBase, LanguageRetrieve
from ..utils import setup_logger

router = APIRouter(prefix="/language")
logger = setup_logger()


@router.post("/create", response_model=LanguageRetrieve)
async def create_language(
    language: LanguageBase,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> LanguageRetrieve | None:
    """
    Create language endpoint. Upsert language to PG database
    """
    language.language_name = language.language_name.upper()
    if not (await is_language_name_unique(language.language_name, asession)):
        raise HTTPException(status_code=400, detail="Language name already exists")

    if language.is_default is True:
        await unset_default_language(asession)

    language_db = await save_language_to_db(language, asession)

    return _convert_language_record_to_schema(language_db)


@router.put("/{language_id}/edit", response_model=LanguageRetrieve)
async def edit_language(
    language_id: int,
    language: LanguageBase,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> LanguageRetrieve | None:
    """
    Edit language endpoint.
    """
    old_language = await get_language_from_db(
        language_id,
        asession,
    )

    if not old_language:
        raise HTTPException(
            status_code=404, detail=f"Language id `{language_id}` not found"
        )
    language.language_name = language.language_name.upper()
    if (old_language.language_name != language.language_name) and (
        not (await is_language_name_unique(language.language_name, asession))
    ):
        raise HTTPException(status_code=400, detail="Language name already exists")

    if language.is_default:
        await unset_default_language(asession)

    updated_language = await update_language_in_db(
        language_id,
        language,
        asession,
    )

    return _convert_language_record_to_schema(updated_language)


@router.get("/list", response_model=list[LanguageRetrieve])
async def retrieve_languages(
    readonly_user: Annotated[AuthenticatedUser, Depends(get_current_readonly_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> List[LanguageRetrieve]:
    """
    Retrieve languages endpoint
    """
    languages = await get_list_of_languages_from_db(asession)
    return [_convert_language_record_to_schema(language) for language in languages]


@router.get("/default", response_model=LanguageRetrieve)
async def retrieve_default_language(
    readonly_user: Annotated[AuthenticatedUser, Depends(get_current_readonly_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> LanguageRetrieve:
    """
    Retrieve default language endpoint
    """
    language = await get_default_language_from_db(asession)
    if not language:
        raise HTTPException(status_code=404, detail="Default language not found")
    return _convert_language_record_to_schema(language)


@router.get("/{language_id}", response_model=LanguageRetrieve)
async def retrieve_language_by_id(
    language_id: int,
    readonly_user: Annotated[AuthenticatedUser, Depends(get_current_readonly_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> LanguageRetrieve:
    """
    Rretrieve language by id endpoint
    """
    language = await get_language_from_db(language_id, asession)
    if not language:
        raise HTTPException(
            status_code=404, detail=f"Language id `{language_id}` not found"
        )
    return _convert_language_record_to_schema(language)


@router.delete("/{language_id}/delete")
async def delete_language(
    language_id: int,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Delete language endpoint
    """
    language = await get_language_from_db(
        language_id,
        asession,
    )

    if not language:
        raise HTTPException(
            status_code=404, detail=f"Language id `{language_id}` not found"
        )

    if language.is_default:
        raise HTTPException(
            status_code=400, detail="Default language cannot be deleted"
        )
    await delete_language_from_db(language_id, asession)


async def unset_default_language(asession: AsyncSession) -> None:
    """
    Unset default language
    """
    default_language = await get_default_language_from_db(asession)

    if default_language:
        default_language.is_default = False
        default_language_schema = _convert_language_record_to_schema(default_language)
        await update_language_in_db(
            default_language.language_id, default_language_schema, asession
        )
    return None


def _convert_language_record_to_schema(language_db: LanguageDB) -> LanguageRetrieve:
    return LanguageRetrieve(
        language_id=language_db.language_id,
        language_name=language_db.language_name,
        is_default=language_db.is_default,
        created_datetime_utc=language_db.created_datetime_utc,
        updated_datetime_utc=language_db.updated_datetime_utc,
    )
