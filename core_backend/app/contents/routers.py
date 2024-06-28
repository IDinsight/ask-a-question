from typing import Annotated, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, UploadFile
from fastapi.exceptions import HTTPException
from pandas.errors import EmptyDataError, ParserError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_async_session
from ..tags.models import TagDB, get_list_of_tag_from_db, save_tag_to_db, validate_tags
from ..tags.schemas import TagCreate, TagRetrieve
from ..users.models import UserDB
from ..utils import setup_logger
from .models import (
    ContentDB,
    ExceedsContentQuotaError,
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

router = APIRouter(prefix="/content", tags=["Content Management"])
logger = setup_logger()


class BulkUploadResponse(BaseModel):
    """
    Pydantic model for the csv-upload response
    """

    tags: List[TagRetrieve]
    contents: List[ContentRetrieve]


@router.post("/", response_model=ContentRetrieve)
async def create_content(
    content: ContentCreate,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> Optional[ContentRetrieve]:
    """
    Create content endpoint. Calls embedding model to get content embedding and
    inserts it to PG database
    """
    is_tag_valid, content_tags = await validate_tags(
        user_db.user_id, content.content_tags, asession
    )
    if not is_tag_valid:
        raise HTTPException(status_code=400, detail=f"Invalid tag ids: {content_tags}")
    content.content_tags = content_tags

    try:
        content_db = await save_content_to_db(
            user_id=user_db.user_id,
            content=content,
            asession=asession,
        )
    except ExceedsContentQuotaError as e:
        raise HTTPException(
            status_code=403, detail="Exceeds content quota for user. {e}"
        ) from e
    else:
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
        raise HTTPException(status_code=400, detail=f"Invalid tag ids: {content_tags}")
    content.content_tags = content_tags
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


@router.post("/csv-upload", response_model=BulkUploadResponse)
async def bulk_upload_contents(
    file: UploadFile,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> Optional[BulkUploadResponse]:
    """
    Upload, check, and ingest contents in bulk from a CSV file.

    Note: If there are any issues with the CSV, the endpoint will return a 400 error
    with the list of issues under detail in the response body.
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
        raise HTTPException(status_code=400, detail=error_list_model.dict())

    df = _load_csv(file)
    await _csv_checks(df=df, user_id=user_db.user_id, asession=asession)

    # Create each new tag in the database
    tags_col = "content_tag_names"
    if "content_tag_names" not in df.columns:
        skip_tags = True
    elif df["content_tag_names"].isnull().all():
        skip_tags = True
    else:
        skip_tags = False

    created_tags: List[TagRetrieve] = []
    if not skip_tags:
        incoming_tags = extract_unique_tags(tags_col=df[tags_col])
        logger.info(f"Tags in CSV: {incoming_tags}")
        tags_in_db = await get_list_of_tag_from_db(
            user_id=user_db.user_id, asession=asession
        )
        logger.info(f"Tags in DB: {tags_in_db}")
        tags_to_create = get_tags_not_in_db(
            tags_in_db=tags_in_db, incoming_tags=incoming_tags
        )
        logger.info(f"Tags to create: {tags_to_create}")
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
        logger.info(f"Tag name to id map: {tag_name_to_id_map}")

    # Add each row to the content database
    created_contents = []
    for _, row in df.iterrows():
        content_tags: List = []  # should be List[TagDB] but clashes with validate_tags
        if not skip_tags:
            if not pd.isna(row[tags_col]):
                tag_names = [
                    tag_name.strip().upper() for tag_name in row[tags_col].split(",")
                ]
                tag_ids = [tag_name_to_id_map[tag_name] for tag_name in tag_names]
                logger.info(f"Tag names: {tag_names}, Tag ids: {tag_ids}")
                is_tag_valid, content_tags = await validate_tags(
                    user_db.user_id, tag_ids, asession
                )

        content = ContentCreate(
            content_title=row["content_title"],
            content_text=row["content_text"],
            content_tags=content_tags,
            content_metadata={},
        )
        content_db = await save_content_to_db(
            user_id=user_db.user_id, content=content, asession=asession
        )
        content_retrieve = _convert_record_to_schema(content_db)
        created_contents.append(content_retrieve)

    return BulkUploadResponse(tags=created_tags, contents=created_contents)


def get_tags_not_in_db(
    tags_in_db: List[TagDB],
    incoming_tags: List[str],
) -> List[str]:
    """
    Compare tags fetched from the DB with incoming tags and return tags not in the DB
    """
    tags_in_db_list = [tag_json.tag_name for tag_json in tags_in_db]
    tags_not_in_db_list = list(set(incoming_tags) - set(tags_in_db_list))

    return tags_not_in_db_list


def extract_unique_tags(tags_col: pd.Series) -> List[str]:
    """
    Get unique UPPERCASE tags from a DataFrame column (comma-separated within column)
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


def _load_csv(file: UploadFile) -> pd.DataFrame:
    """
    Load the CSV file into a pandas DataFrame
    """

    try:
        df = pd.read_csv(file.file, dtype=str)
    except EmptyDataError as e:
        error_list_model = CustomErrorList(
            errors=[
                CustomError(
                    type="empty_data",
                    description="The CSV file is empty",
                )
            ]
        )
        raise HTTPException(status_code=400, detail=error_list_model.dict()) from e
    except ParserError as e:
        error_list_model = CustomErrorList(
            errors=[
                CustomError(
                    type="parse_error",
                    description="CSV is unreadable (parsing error)",
                )
            ]
        )
        raise HTTPException(status_code=400, detail=error_list_model.dict()) from e
    except UnicodeDecodeError as e:
        error_list_model = CustomErrorList(
            errors=[
                CustomError(
                    type="encoding_error",
                    description="CSV is unreadable (encoding error)",
                )
            ]
        )
        raise HTTPException(status_code=400, detail=error_list_model.dict()) from e
    if df.empty:
        error_list_model = CustomErrorList(
            errors=[
                CustomError(
                    type="no_rows_csv",
                    description="The CSV file is empty",
                )
            ]
        )
        raise HTTPException(status_code=400, detail=error_list_model.dict())

    return df


async def _csv_checks(df: pd.DataFrame, user_id: int, asession: AsyncSession) -> None:
    """
    Perform checks on the CSV file to ensure it meets the requirements
    """

    # check if content_title and content_text columns are present
    cols = df.columns
    error_list = []
    if "content_title" not in cols or "content_text" not in cols:
        error_list.append(
            CustomError(
                type="missing_columns",
                description=(
                    "File must have 'content_title' and 'content_text' columns."
                ),
            )
        )
        # if either of these columns are missing, skip further checks
        error_list_model = CustomErrorList(errors=error_list)
        raise HTTPException(status_code=400, detail=error_list_model.dict())
    else:
        # strip columns to catch duplicates better and empty cells
        df["content_title"] = df["content_title"].str.strip()
        df["content_text"] = df["content_text"].str.strip()

        # set any empty strings to None
        df = df.replace("", None)

        # check if there are any empty values in either column
        if df["content_title"].isnull().any():
            error_list.append(
                CustomError(
                    type="empty_title",
                    description=(
                        "One or more empty content titles found in the CSV file."
                    ),
                )
            )
        if df["content_text"].isnull().any():
            error_list.append(
                CustomError(
                    type="empty_text",
                    description=(
                        "One or more empty content texts found in the CSV file."
                    ),
                )
            )
        # check if any title exceeds 150 characters
        if df["content_title"].str.len().max() > 150:
            error_list.append(
                CustomError(
                    type="title_too_long",
                    description="One or more content titles exceed 150 characters.",
                )
            )
        # check if any text exceeds 2000 characters
        if df["content_text"].str.len().max() > 2000:
            error_list.append(
                CustomError(
                    type="texts_too_long",
                    description="One or more content texts exceed 150 characters.",
                )
            )

        # check if there are duplicates in either column
        if df.duplicated(subset=["content_title"]).any():
            error_list.append(
                CustomError(
                    type="duplicate_titles",
                    description="Duplicate content titles found in the CSV file.",
                )
            )
        if df.duplicated(subset=["content_text"]).any():
            error_list.append(
                CustomError(
                    type="duplicate_texts",
                    description="Duplicate content texts found in the CSV file.",
                )
            )

        # check for duplicate titles and texts between the CSV and the database
        contents_in_db = await get_list_of_content_from_db(
            user_id, offset=0, limit=None, asession=asession
        )
        content_titles_in_db = [c.content_title.strip() for c in contents_in_db]
        content_texts_in_db = [c.content_text.strip() for c in contents_in_db]
        if df["content_title"].isin(content_titles_in_db).any():
            error_list.append(
                CustomError(
                    type="title_in_db",
                    description=(
                        "One or more content titles already exist in the database."
                    ),
                )
            )
        if df["content_text"].isin(content_texts_in_db).any():
            error_list.append(
                CustomError(
                    type="text_in_db",
                    description=(
                        "One or more content texts already exist in the database."
                    ),
                )
            )

        if error_list:
            error_list_model = CustomErrorList(errors=error_list)
            raise HTTPException(status_code=400, detail=error_list_model.dict())


def _convert_record_to_schema(record: ContentDB) -> ContentRetrieve:
    """
    Convert models.ContentDB models to ContentRetrieve schema
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
    )

    return content_retrieve


def _convert_tag_record_to_schema(record: TagDB) -> TagRetrieve:
    """
    Convert models.TagDB models to TagRetrieve schema
    """

    tag_retrieve = TagRetrieve(
        tag_id=record.tag_id,
        user_id=record.user_id,
        tag_name=record.tag_name,
        created_datetime_utc=record.created_datetime_utc,
        updated_datetime_utc=record.updated_datetime_utc,
    )

    return tag_retrieve
