from typing import Annotated, List

import pandas as pd
from fastapi import APIRouter, Depends, UploadFile
from fastapi.exceptions import HTTPException
from pandas.errors import EmptyDataError, ParserError
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
        raise HTTPException(status_code=400, detail=f"Invalid tag ids: {content_tags}")
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
        raise HTTPException(status_code=400, detail=f"Invalid tag ids: {content_tags}")
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


@router.post("/csv-upload", response_model=dict)
async def upload_contents_in_bulk(
    file: UploadFile,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Upload and process contents in bulk from a CSV file.
    """

    # TODO: deal with tags!

    # Ensure the file is a CSV
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400, detail="Invalid file format. Please upload a CSV file."
        )

    df = _load_csv(file)
    await _csv_checks(df=df, user_id=user_db.user_id, asession=asession)

    # Add each row to the content database
    for _, row in df.iterrows():
        content = ContentCreate(
            content_title=row["content_title"],
            content_text=row["content_text"],
            content_language=row.get("content_language", "ENGLISH"),
            content_tags=[],
            content_metadata=row.get("content_metadata", {}),
        )
        await save_content_to_db(
            user_id=user_db.user_id, content=content, asession=asession
        )

    return {"message": f"Added {len(df)} new contents."}


def _load_csv(file: UploadFile) -> pd.DataFrame:
    """
    Load the CSV file into a pandas DataFrame
    """

    try:
        df = pd.read_csv(file.file)
        return df
    except EmptyDataError as e:
        raise HTTPException(status_code=400, detail="The CSV file is empty.") from e
    except ParserError as e:
        raise HTTPException(
            status_code=400, detail="CSV is unreadable (parsing error)"
        ) from e
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=400, detail="CSV is unreadable (encoding error)"
        ) from e


async def _csv_checks(df: pd.DataFrame, user_id: int, asession: AsyncSession) -> None:
    """
    Perform checks on the CSV file to ensure it meets the requirements
    """

    # check if content_title and content_text columns are present
    cols = df.columns
    if "content_title" not in cols or "content_text" not in cols:
        raise HTTPException(
            status_code=400,
            detail="File must have 'content_title' and 'content_text' columns.",
        )
    # check if there are any empty values in either column
    if df["content_title"].isnull().any():
        raise HTTPException(
            status_code=400,
            detail="One or more empty content titles found in the CSV file.",
        )
    if df["content_text"].isnull().any():
        raise HTTPException(
            status_code=400,
            detail="One or more empty content texts found in the CSV file.",
        )
    # check if any title exceeds 150 characters
    if df["content_title"].str.len().max() > 150:
        raise HTTPException(
            status_code=400, detail="One or more content titles exceed 150 characters."
        )
    # check if any text exceeds 2000 characters
    if df["content_text"].str.len().max() > 2000:
        raise HTTPException(
            status_code=400, detail="One or more content texts exceed 2000 characters."
        )

    # check if there are duplicates in either column
    if df.duplicated(subset=["content_title"]).any():
        raise HTTPException(
            status_code=400,
            detail="Duplicate content titles found in the CSV file.",
        )
    if df.duplicated(subset=["content_text"]).any():
        raise HTTPException(
            status_code=400,
            detail="Duplicate content text found in the CSV file.",
        )

    # check for duplicate titles and texts between the CSV and the database
    contents_in_db = await get_list_of_content_from_db(
        user_id, offset=0, limit=None, asession=asession
    )
    content_titles_in_db = [c.content_title for c in contents_in_db]
    content_texts_in_db = [c.content_text for c in contents_in_db]
    if df["content_title"].isin(content_titles_in_db).any():
        raise HTTPException(
            status_code=400,
            detail="One or more content titles already exist in the database.",
        )
    if df["content_text"].isin(content_texts_in_db).any():
        raise HTTPException(
            status_code=400,
            detail="One or more content texts already exist in the database.",
        )


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
