"""This module contains the FastAPI router for the content management endpoints."""

from typing import Annotated, List, Optional

import pandas as pd
import sqlalchemy.exc
from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.exceptions import HTTPException
from pandas.errors import EmptyDataError, ParserError
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..config import CHECK_CONTENT_LIMIT
from ..database import get_async_session
from ..tags.models import TagDB, get_list_of_tag_from_db, save_tag_to_db, validate_tags
from ..tags.schemas import TagCreate, TagRetrieve
from ..users.models import UserDB, get_content_quota_by_userid
from ..utils import setup_logger
from .models import (
    ContentDB,
    archive_content_from_db,
    delete_content_from_db,
    get_content_from_db,
    get_list_of_content_from_db,
    save_content_to_db,
    update_content_in_db,
)
from .schemas import (
    ContentCreate,
    ContentRetrieve,
    CustomError,
    CustomErrorList,
)

TAG_METADATA = {
    "name": "Content management",
    "description": "_Requires user login._ Manage content and tags to be used for "
    "question answering.",
}

router = APIRouter(prefix="/content", tags=[TAG_METADATA["name"]])
logger = setup_logger()


class BulkUploadResponse(BaseModel):
    """
    Pydantic model for the csv-upload response
    """

    tags: List[TagRetrieve]
    contents: List[ContentRetrieve]


class ExceedsContentQuotaError(Exception):
    """
    Exception raised when a user is attempting to add
    more content that their quota allows.
    """


@router.post("/", response_model=ContentRetrieve)
async def create_content(
    content: ContentCreate,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> Optional[ContentRetrieve]:
    """
    Create new content.

    ⚠️ To add tags, first use the tags endpoint to create tags.
    """

    is_tag_valid, content_tags = await validate_tags(
        user_db.user_id, content.content_tags, asession
    )
    if not is_tag_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tag ids: {content_tags}",
        )
    content.content_tags = content_tags

    # Check if the user would exceed their content quota
    if CHECK_CONTENT_LIMIT:
        try:
            await _check_content_quota_availability(
                user_id=user_db.user_id,
                n_contents_to_add=1,
                asession=asession,
            )
        except ExceedsContentQuotaError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Exceeds content quota for user. {e}",
            ) from e

    content_db = await save_content_to_db(
        user_id=user_db.user_id,
        content=content,
        exclude_archived=False,  # Don't exclude for newly saved content!
        asession=asession,
    )
    return _convert_record_to_schema(content_db)


@router.put("/{content_id}", response_model=ContentRetrieve)
async def edit_content(
    content_id: int,
    content: ContentCreate,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    exclude_archived: bool = True,
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve:
    """
    Edit pre-existing content.
    """

    old_content = await get_content_from_db(
        user_id=user_db.user_id,
        content_id=content_id,
        exclude_archived=exclude_archived,
        asession=asession,
    )

    if not old_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content id `{content_id}` not found",
        )

    is_tag_valid, content_tags = await validate_tags(
        user_db.user_id, content.content_tags, asession
    )
    if not is_tag_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tag ids: {content_tags}",
        )
    content.content_tags = content_tags
    content.is_archived = old_content.is_archived
    updated_content = await update_content_in_db(
        user_id=user_db.user_id,
        content_id=content_id,
        content=content,
        asession=asession,
    )

    return _convert_record_to_schema(updated_content)


@router.get("/", response_model=List[ContentRetrieve])
async def retrieve_content(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 50,
    exclude_archived: bool = True,
    asession: AsyncSession = Depends(get_async_session),
) -> List[ContentRetrieve]:
    """
    Retrieve all contents
    """

    records = await get_list_of_content_from_db(
        user_id=user_db.user_id,
        offset=skip,
        limit=limit,
        exclude_archived=exclude_archived,
        asession=asession,
    )
    contents = [_convert_record_to_schema(c) for c in records]
    return contents


@router.patch("/{content_id}")
async def archive_content(
    content_id: int,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Archive content by ID.
    """

    record = await get_content_from_db(
        user_id=user_db.user_id,
        content_id=content_id,
        asession=asession,
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content id `{content_id}` not found",
        )
    await archive_content_from_db(
        user_id=user_db.user_id,
        content_id=content_id,
        asession=asession,
    )


@router.delete("/{content_id}")
async def delete_content(
    content_id: int,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Delete content by ID
    """

    record = await get_content_from_db(
        user_id=user_db.user_id,
        content_id=content_id,
        asession=asession,
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content id `{content_id}` not found",
        )

    try:
        await delete_content_from_db(
            user_id=user_db.user_id,
            content_id=content_id,
            asession=asession,
        )
    except sqlalchemy.exc.IntegrityError as e:
        logger.error(f"Error deleting content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Deletion of content with feedback is not allowed.",
        ) from e


@router.get("/{content_id}", response_model=ContentRetrieve)
async def retrieve_content_by_id(
    content_id: int,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    exclude_archived: bool = True,
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve:
    """
    Retrieve content by ID
    """

    record = await get_content_from_db(
        user_id=user_db.user_id,
        content_id=content_id,
        exclude_archived=exclude_archived,
        asession=asession,
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content id `{content_id}` not found",
        )

    return _convert_record_to_schema(record)


@router.post("/csv-upload", response_model=BulkUploadResponse)
async def bulk_upload_contents(
    file: UploadFile,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    exclude_archived: bool = True,
    asession: AsyncSession = Depends(get_async_session),
) -> BulkUploadResponse:
    """Upload, check, and ingest contents in bulk from a CSV file.

    Note: If there are any issues with the CSV, the endpoint will return a 400 error
    with the list of issues under 'detail' in the response body.
    """

    # Ensure the file is a CSV
    if file.filename is None or not file.filename.endswith(".csv"):
        error_list_model = CustomErrorList(
            errors=[
                CustomError(
                    type="invalid_format",
                    description="Please upload a CSV file.",
                )
            ]
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_list_model.model_dump(),
        )

    df = _load_csv(file)
    await _csv_checks(df=df, user_id=user_db.user_id, asession=asession)

    # Create each new tag in the database
    tags_col = "tags"
    created_tags: List[TagRetrieve] = []
    tag_name_to_id_map: dict[str, int] = {}
    skip_tags = tags_col not in df.columns or df[tags_col].isnull().all()
    if not skip_tags:
        incoming_tags = _extract_unique_tags(tags_col=df[tags_col])
        tags_in_db = await get_list_of_tag_from_db(
            user_id=user_db.user_id, asession=asession
        )
        tags_to_create = _get_tags_not_in_db(
            tags_in_db=tags_in_db, incoming_tags=incoming_tags
        )
        for tag in tags_to_create:
            tag_create = TagCreate(tag_name=tag)
            tag_db = await save_tag_to_db(
                user_id=user_db.user_id,
                tag=tag_create,
                asession=asession,
            )
            tags_in_db.append(tag_db)

            # Convert the tag record to a schema (for response)
            tag_retrieve = _convert_tag_record_to_schema(tag_db)
            created_tags.append(tag_retrieve)

        # tag name to tag id mapping
        tag_name_to_id_map = {tag.tag_name: tag.tag_id for tag in tags_in_db}

    # Add each row to the content database
    created_contents = []
    for _, row in df.iterrows():
        content_tags: List = []  # should be List[TagDB] but clashes with validate_tags
        if tag_name_to_id_map and not pd.isna(row[tags_col]):
            tag_names = [
                tag_name.strip().upper() for tag_name in row[tags_col].split(",")
            ]
            tag_ids = [tag_name_to_id_map[tag_name] for tag_name in tag_names]
            _, content_tags = await validate_tags(user_db.user_id, tag_ids, asession)

        content = ContentCreate(
            content_title=row["title"],
            content_text=row["text"],
            content_tags=content_tags,
            content_metadata={},
        )

        content_db = await save_content_to_db(
            user_id=user_db.user_id,
            content=content,
            exclude_archived=exclude_archived,
            asession=asession,
        )
        content_retrieve = _convert_record_to_schema(content_db)
        created_contents.append(content_retrieve)

    return BulkUploadResponse(tags=created_tags, contents=created_contents)


def _load_csv(file: UploadFile) -> pd.DataFrame:
    """Load the CSV file into a pandas DataFrame.

    Parameters
    ----------
    file
        The CSV file to load.

    Returns
    -------
    pd.DataFrame
        The loaded DataFrame.

    Raises
    ------
    HTTPException
        If the CSV file is empty or unreadable.
    """

    try:
        df = pd.read_csv(file.file, dtype=str)
    except (EmptyDataError, ParserError, UnicodeDecodeError) as e:
        error_type = {
            EmptyDataError: "empty_data",
            ParserError: "parse_error",
            UnicodeDecodeError: "encoding_error",
        }.get(type(e), "unknown_error")
        error_description = {
            "empty_data": "The CSV file is empty",
            "parse_error": "CSV is unreadable (parsing error)",
            "encoding_error": "CSV is unreadable (encoding error)",
        }.get(error_type, "An unknown error occurred")
        error_list_model = CustomErrorList(
            errors=[CustomError(type=error_type, description=error_description)]
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_list_model.model_dump(),
        ) from e
    if df.empty:
        error_list_model = CustomErrorList(
            errors=[
                CustomError(
                    type="no_rows_csv",
                    description="The CSV file is empty",
                )
            ]
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_list_model.model_dump(),
        )

    return df


async def check_content_quota(
    user_id: int,
    n_contents_to_add: int,
    asession: AsyncSession,
    error_list: List[CustomError],
) -> None:
    """Check if the user would exceed their content quota given the number of new
    contents to add.

    Parameters
    ----------
    user_id
        The user ID to check the content quota for.
    n_contents_to_add
        The number of new contents to add.
    asession
        `AsyncSession` object for database transactions.
    error_list
        The list of errors to append to.
    """

    try:
        await _check_content_quota_availability(
            user_id=user_id, n_contents_to_add=n_contents_to_add, asession=asession
        )
    except ExceedsContentQuotaError as e:
        error_list.append(CustomError(type="exceeds_quota", description=str(e)))


async def check_db_duplicates(
    df: pd.DataFrame,
    user_id: int,
    asession: AsyncSession,
    error_list: List[CustomError],
) -> None:
    """Check for duplicates between the CSV and the database.

    Parameters
    ----------
    df
        The DataFrame to check.
    user_id
        The user ID to check the content duplicates for.
    asession
        `AsyncSession` object for database transactions.
    error_list
        The list of errors to append to.
    """

    contents_in_db = await get_list_of_content_from_db(
        user_id=user_id, offset=0, limit=None, asession=asession
    )
    content_titles_in_db = {c.content_title.strip() for c in contents_in_db}
    content_texts_in_db = {c.content_text.strip() for c in contents_in_db}

    if df["title"].isin(content_titles_in_db).any():
        error_list.append(
            CustomError(
                type="title_in_db",
                description="One or more content titles already exist in the database.",
            )
        )
    if df["text"].isin(content_texts_in_db).any():
        error_list.append(
            CustomError(
                type="text_in_db",
                description="One or more content texts already exist in the database.",
            )
        )


async def _csv_checks(df: pd.DataFrame, user_id: int, asession: AsyncSession) -> None:
    """Perform checks on the CSV file to ensure it meets the requirements.

    Parameters
    ----------
    df
        The DataFrame to check.
    user_id
        The user ID to check the content quota for.
    asession
        `AsyncSession` object for database transactions.

    Raises
    ------
    HTTPException
        If the CSV file does not meet the requirements.
    """

    error_list: List[CustomError] = []
    check_required_columns(df, error_list)
    await check_content_quota(user_id, len(df), asession, error_list)
    clean_dataframe(df)
    check_empty_values(df, error_list)
    check_length_constraints(df, error_list)
    check_duplicates(df, error_list)
    await check_db_duplicates(df, user_id, asession, error_list)

    if error_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=CustomErrorList(errors=error_list).model_dump(),
        )


def check_duplicates(df: pd.DataFrame, error_list: List[CustomError]) -> None:
    """Check for duplicates in the DataFrame.

    Parameters
    ----------
    df
        The DataFrame to check.
    error_list
        The list of errors to append to.
    """

    if df.duplicated(subset=["title"]).any():
        error_list.append(
            CustomError(
                type="duplicate_titles",
                description="Duplicate content titles found in the CSV file.",
            )
        )
    if df.duplicated(subset=["text"]).any():
        error_list.append(
            CustomError(
                type="duplicate_texts",
                description="Duplicate content texts found in the CSV file.",
            )
        )


def check_empty_values(df: pd.DataFrame, error_list: List[CustomError]) -> None:
    """Check for empty values in the DataFrame.

    Parameters
    ----------
    df
        The DataFrame to check.
    error_list
        The list of errors to append to.
    """

    if df["title"].isnull().any():
        error_list.append(
            CustomError(
                type="empty_title",
                description="One or more empty content titles found in the CSV file.",
            )
        )
    if df["text"].isnull().any():
        error_list.append(
            CustomError(
                type="empty_text",
                description="One or more empty content texts found in the CSV file.",
            )
        )


def check_length_constraints(df: pd.DataFrame, error_list: List[CustomError]) -> None:
    """Check for length constraints in the DataFrame.

    Parameters
    ----------
    df
        The DataFrame to check.
    error_list
        The list of errors to append to.
    """

    if df["title"].str.len().max() > 150:
        error_list.append(
            CustomError(
                type="title_too_long",
                description="One or more content titles exceed 150 characters.",
            )
        )
    if df["text"].str.len().max() > 2000:
        error_list.append(
            CustomError(
                type="texts_too_long",
                description="One or more content texts exceed 2000 characters.",
            )
        )


def check_required_columns(df: pd.DataFrame, error_list: List[CustomError]) -> None:
    """Check if the CSV file has the required columns.

    Parameters
    ----------
    df
        The DataFrame to check.
    error_list
        The list of errors to append to.

    Raises
    ------
    HTTPException
        If the CSV file does not have the required columns.
    """

    required_columns = {"title", "text"}
    if not required_columns.issubset(df.columns):
        error_list.append(
            CustomError(
                type="missing_columns",
                description="File must have 'title' and 'text' columns.",
            )
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=CustomErrorList(errors=error_list).model_dump(),
        )


def clean_dataframe(df: pd.DataFrame) -> None:
    """Clean the DataFrame by stripping whitespace and replacing empty strings.

    Parameters
    ----------
    df
        The DataFrame to clean.
    """

    df["title"] = df["title"].str.strip()
    df["text"] = df["text"].str.strip()
    df.replace("", None, inplace=True)


async def _check_content_quota_availability(
    user_id: int,
    n_contents_to_add: int,
    asession: AsyncSession,
) -> None:
    """Raise an error if user would reach their content quota given n new contents.

    Parameters
    ----------
    user_id
        The user ID to check the content quota for.
    n_contents_to_add
        The number of new contents to add.
    asession
        `AsyncSession` object for database transactions.

    Raises
    ------
    ExceedsContentQuotaError
        If the user would exceed their content quota.
    """

    # get content_quota value for this user from UserDB
    content_quota = await get_content_quota_by_userid(
        user_id=user_id, asession=asession
    )

    # if content_quota is None, then there is no limit
    if content_quota is not None:
        # get the number of contents this user has already added
        stmt = select(ContentDB).where(
            (ContentDB.user_id == user_id) & (~ContentDB.is_archived)
        )
        user_active_contents = (await asession.execute(stmt)).all()
        n_contents_in_db = len(user_active_contents)

        # error if total of existing and new contents exceeds the quota
        if (n_contents_in_db + n_contents_to_add) > content_quota:
            if n_contents_in_db > 0:
                raise ExceedsContentQuotaError(
                    f"Adding {n_contents_to_add} new contents to the already existing "
                    f"{n_contents_in_db} in the database would exceed the allowed "
                    f"limit of {content_quota} contents."
                )
            else:
                raise ExceedsContentQuotaError(
                    f"Adding {n_contents_to_add} new contents to the database would "
                    f"exceed the allowed limit of {content_quota} contents."
                )


def _extract_unique_tags(tags_col: pd.Series) -> List[str]:
    """Get unique UPPERCASE tags from a DataFrame column (comma-separated within
    column).

    Parameters
    ----------
    tags_col
        The column containing tags.

    Returns
    -------
    List[str]
        A list of unique tags.
    """

    # prep col
    tags_col = tags_col.dropna().astype(str)
    # split and explode to have one tag per row
    tags_flat = tags_col.str.split(",").explode()
    # strip and uppercase
    tags_flat = tags_flat.str.strip().str.upper()
    # get unique tags as a list
    tags_unique_list = tags_flat.unique().tolist()
    return tags_unique_list


def _get_tags_not_in_db(
    tags_in_db: List[TagDB],
    incoming_tags: List[str],
) -> List[str]:
    """Compare tags fetched from the DB with incoming tags and return tags not in the
    DB.

    Parameters
    ----------
    tags_in_db
        List of `TagDB` objects fetched from the database.
    incoming_tags
        List of incoming tags.

    Returns
    -------
    List[str]
        List of tags not in the database.
    """

    tags_in_db_list = [tag_json.tag_name for tag_json in tags_in_db]
    tags_not_in_db_list = list(set(incoming_tags) - set(tags_in_db_list))

    return tags_not_in_db_list


def _convert_record_to_schema(record: ContentDB) -> ContentRetrieve:
    """Convert `models.ContentDB` models to `ContentRetrieve` schema.

    Parameters
    ----------
    record
        `ContentDB` object to convert.

    Returns
    -------
    ContentRetrieve
        `ContentRetrieve` object of the converted record.
    """

    content_retrieve = ContentRetrieve(
        content_id=record.content_id,
        user_id=record.user_id,
        content_title=record.content_title,
        content_text=record.content_text,
        content_tags=[tag.tag_id for tag in record.content_tags],
        positive_votes=record.positive_votes,
        negative_votes=record.negative_votes,
        content_metadata=record.content_metadata,
        created_datetime_utc=record.created_datetime_utc,
        updated_datetime_utc=record.updated_datetime_utc,
        is_archived=record.is_archived,
    )

    return content_retrieve


def _convert_tag_record_to_schema(record: TagDB) -> TagRetrieve:
    """Convert `models.TagDB` models to `TagRetrieve` schema.

    Parameters
    ----------
    record
        `TagDB` object to convert.

    Returns
    -------
    TagRetrieve
        `TagRetrieve` object of the converted record.
    """

    tag_retrieve = TagRetrieve(
        tag_id=record.tag_id,
        user_id=record.user_id,
        tag_name=record.tag_name,
        created_datetime_utc=record.created_datetime_utc,
        updated_datetime_utc=record.updated_datetime_utc,
    )

    return tag_retrieve
