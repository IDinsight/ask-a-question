"""This module contains FastAPI routers for content management endpoints."""

from typing import Annotated, Optional

import pandas as pd
import sqlalchemy.exc
from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.exceptions import HTTPException
from langfuse.decorators import observe  # type: ignore
from pandas.errors import EmptyDataError, ParserError
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_workspace_name
from ..config import CHECK_CONTENT_LIMIT
from ..database import get_async_session
from ..tags.models import (
    TagDB,
    get_list_of_tag_from_db,
    save_tag_to_db,
    validate_tags,
)
from ..tags.schemas import TagCreate, TagRetrieve
from ..users.models import UserDB, user_has_required_role_in_workspace
from ..users.schemas import UserRoles
from ..utils import EmbeddingCallException, setup_logger
from ..workspaces.utils import (
    get_content_quota_by_workspace_id,
    get_workspace_by_workspace_name,
)
from .models import (
    ContentDB,
    archive_content_from_db,
    delete_content_from_db,
    get_content_from_db,
    get_list_of_content_from_db,
    get_next_unvalidated_content_card,
    get_unvalidated_count,
    mark_content_as_validated,
    save_content_to_db,
    update_content_in_db,
    validate_related_contents,
)
from .schemas import ContentCreate, ContentRetrieve, CustomError, CustomErrorList

TAG_METADATA = {
    "name": "Content management",
    "description": "_Requires user login._ Manage content and tags to be used for "
    "question answering.",
}

router = APIRouter(prefix="/content", tags=[TAG_METADATA["name"]])
logger = setup_logger()


class BulkUploadResponse(BaseModel):
    """Pydantic model for the CSV-upload response."""

    contents: list[ContentRetrieve]
    tags: list[TagRetrieve]


class ExceedsContentQuotaError(Exception):
    """Exception raised when a user is attempting to add more content that their quota
    allows.
    """


@router.post("/", response_model=ContentRetrieve)
@observe()
async def create_content(
    content: ContentCreate,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> Optional[ContentRetrieve]:
    """Create new content.

    NB: ⚠️ To add tags, first use the `tags` endpoint to create tags.

    NB: Content is now created within a specified workspace.

    The process is as follows:

    1. Parameters for the endpoint are checked first.
    2. Check if the content tags are valid.
    3, Check if the created content would exceed the workspace content quota.
    4. Save the content to the `ContentDB` database.

    Parameters
    ----------
    content
        The content object to create.
    calling_user_db
        The user object associated with the user that is creating the content.
    workspace_name
        The name of the workspace to create the content in.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    Optional[ContentRetrieve]
        The created content.

    Raises
    ------
    HTTPException
        If the user does not have the required role to create content in the workspace.
        If the content tags are invalid or the user would exceed their content quota.
        If the embedding of the content fails.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to create content in the "
            "workspace.",
        )

    # 2.
    workspace_id = workspace_db.workspace_id
    is_tag_valid, content_tags = await validate_tags(
        asession=asession, tags=content.content_tags, workspace_id=workspace_id
    )
    if not is_tag_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tag IDs: {content_tags}",
        )
    content.content_tags = content_tags

    # 3.
    if content.related_contents_id:
        is_related_content_valid, related_contents = await validate_related_contents(
            asession=asession,
            related_contents=content.related_contents_id,
            workspace_id=workspace_id,
        )
        if not is_related_content_valid and len(related_contents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid related content IDs: {content.related_contents_id}",
            )
        content.related_contents_id = related_contents
    # 4.
    if CHECK_CONTENT_LIMIT:
        try:
            await _check_content_quota_availability(
                asession=asession, n_contents_to_add=1, workspace_id=workspace_id
            )
        except ExceedsContentQuotaError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Exceeds content quota for workspace. {e}",
            ) from e

    # 5.
    try:
        content_db = await save_content_to_db(
            asession=asession,
            content=content,
            exclude_archived=False,  # Don't exclude for newly saved content!
            workspace_id=workspace_id,
        )
    except EmbeddingCallException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error embedding content. Please check embedding service.",
        ) from e
    return _convert_record_to_schema(record=content_db)


@router.put("/{content_id}", response_model=ContentRetrieve)
@observe()
async def edit_content(
    content_id: int,
    content: ContentCreate,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    exclude_archived: bool = True,
    exclude_unvalidated: bool = False,
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve:
    """Edit pre-existing content.

    Parameters
    ----------
    content_id
        The ID of the content to edit.
    content
        The content to edit.
    calling_user_db
        The user object associated with the user that is editing the content.
    workspace_name
        The name of the workspace that the content belongs in.
    exclude_archived
        Specifies whether to exclude archived contents.
    exclude_unvalidated
        Specifies whether to exclude unvalidated contents.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    ContentRetrieve
        The edited content.

    Raises
    ------
    HTTPException
        If the user does not have the required role to edit content in the workspace.
        If the content to edit is not found.
        If the tags are invalid.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to edit content in the "
            "workspace.",
        )

    workspace_id = workspace_db.workspace_id
    old_content = await get_content_from_db(
        asession=asession,
        content_id=content_id,
        exclude_archived=exclude_archived,
        exclude_unvalidated=exclude_unvalidated,
        workspace_id=workspace_id,
    )

    if not old_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content ID `{content_id}` not found",
        )

    is_tag_valid, content_tags = await validate_tags(
        asession=asession, tags=content.content_tags, workspace_id=workspace_id
    )

    if not is_tag_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tag IDs: {content_tags}",
        )

    content.content_tags = content_tags
    if content.related_contents_id:
        is_related_content_valid, related_contents = await validate_related_contents(
            asession=asession,
            related_contents=content.related_contents_id,
            workspace_id=workspace_id,
        )
        if not is_related_content_valid and len(related_contents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid related content IDs: {content.related_contents_id}",
            )
        content.related_contents_id = related_contents
    content.is_archived = old_content.is_archived
    try:
        updated_content = await update_content_in_db(
            asession=asession,
            content=content,
            content_id=content_id,
            workspace_id=workspace_id,
        )
    except EmbeddingCallException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error embedding content. Please check embedding service.",
        ) from e

    return _convert_record_to_schema(record=updated_content)


@router.get("/", response_model=list[ContentRetrieve])
async def retrieve_content(
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    skip: int = 0,
    limit: int = 50,
    exclude_archived: bool = True,
    exclude_unvalidated: bool = True,
    asession: AsyncSession = Depends(get_async_session),
) -> list[ContentRetrieve]:
    """Retrieve all contents for the specified workspace.

    Parameters
    ----------
    workspace_name
        The name of the workspace to retrieve content from.
    skip
        The number of contents to skip.
    limit
        The maximum number of contents to retrieve.
    exclude_archived
        Specifies whether to exclude archived contents.
    exclude_unvalidated
        Specifies whether to exclude unvalidated contents.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[ContentRetrieve]
        The retrieved contents from the specified workspace.
    """
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    records = await get_list_of_content_from_db(
        asession=asession,
        exclude_archived=exclude_archived,
        exclude_unvalidated=exclude_unvalidated,
        limit=limit,
        offset=skip,
        workspace_id=workspace_db.workspace_id,
    )
    contents = [_convert_record_to_schema(record=c) for c in records]
    return contents


@router.get("/next-unvalidated", response_model=ContentRetrieve)
async def get_next_unvalidated_content(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve:
    """Retrieve the next unvalidated content card for the specified workspace.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user making the request.
    workspace_name
        The name of the workspace to retrieve the content from.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    ContentRetrieve
        The next unvalidated content card.

    Raises
    ------
    HTTPException
        If the user does not have the required role to access unvalidated content.
        If no unvalidated content is found.
    """
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "User does not have the required role to access "
                "unvalidated content in the workspace."
            ),
        )

    workspace_id = workspace_db.workspace_id
    content_row = await get_next_unvalidated_content_card(
        asession=asession, workspace_id=workspace_id
    )

    if not content_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No unvalidated content found.",
        )
    return _convert_record_to_schema(record=content_row)


@router.patch("/validate/{content_id}")
async def validate_content_card(
    content_id: int,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """Validate content card by ID

    Parameters
    ----------
    content_id
        The ID of the content to validate.
    calling_user_db
        The user object associated with the user that is archiving the content.
    workspace_name
        The name of the workspace to validate content in.
    asession
        The SQLAlchemy async session to use for all database connections.

    Raises
    ------
    HTTPException
        If the user does not have the required role to validate content
        in the workspace. If the content is not found.
    """
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to validate content in the "
            "workspace.",
        )

    workspace_id = workspace_db.workspace_id
    record = await get_content_from_db(
        asession=asession,
        content_id=content_id,
        workspace_id=workspace_id,
        exclude_unvalidated=False,
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content ID `{content_id}` not found",
        )

    await mark_content_as_validated(
        asession=asession, content_id=content_id, workspace_id=workspace_id
    )

    return


@router.get("/unvalidated-count")
async def get_unvalidated_card_count(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> int:
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to validate content in the "
            "workspace.",
        )
    workspace_id = workspace_db.workspace_id
    count = await get_unvalidated_count(asession=asession, workspace_id=workspace_id)
    if count is None:
        return -1
    return count


@router.patch("/{content_id}")
async def archive_content(
    content_id: int,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
    exclude_unvalidated: bool = False,
) -> None:
    """Archive content by ID.

    Parameters
    ----------
    content_id
        The ID of the content to archive.
    calling_user_db
        The user object associated with the user that is archiving the content.
    workspace_name
        The name of the workspace to archive content in.
    asession
        The SQLAlchemy async session to use for all database connections.
    exclude_unvalidated
        Specifies whether to exclude unvalidated contents.

    Raises
    ------
    HTTPException
        If the user does not have the required role to archive content in the workspace.
        If the content is not found.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to archive content in the "
            "workspace.",
        )

    workspace_id = workspace_db.workspace_id
    record = await get_content_from_db(
        asession=asession,
        content_id=content_id,
        workspace_id=workspace_id,
        exclude_unvalidated=exclude_unvalidated,
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content ID `{content_id}` not found",
        )

    await archive_content_from_db(
        asession=asession, content_id=content_id, workspace_id=workspace_id
    )


@router.delete("/{content_id}")
async def delete_content(
    content_id: int,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
    exclude_archived: bool = True,
    exclude_unvalidated: bool = False,
) -> None:
    """Delete content by ID.

    Parameters
    ----------
    content_id
        The ID of the content to delete.
    calling_user_db
        The user object associated with the user that is deleting the content.
    workspace_name
        The name of the workspace to delete content from.
    asession
        The SQLAlchemy async session to use for all database connections.
    exclude_archived
        Specifies whether to exclude archived contents.
    exclude_unvalidated
        Specifies whether to exclude unvalidated contents.

    Raises
    ------
    HTTPException
        If the user does not have the required role to delete content in the workspace.
        If the content is not found.
        If the deletion of the content with feedback is not allowed.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to delete content in the "
            "workspace.",
        )

    workspace_id = workspace_db.workspace_id
    record = await get_content_from_db(
        asession=asession,
        content_id=content_id,
        exclude_archived=exclude_archived,
        exclude_unvalidated=exclude_unvalidated,
        workspace_id=workspace_id,
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content ID `{content_id}` not found",
        )

    try:
        await delete_content_from_db(
            asession=asession, content_id=content_id, workspace_id=workspace_id
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
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    exclude_archived: bool = True,
    exclude_unvalidated: bool = True,
    asession: AsyncSession = Depends(get_async_session),
) -> ContentRetrieve:
    """Retrieve content by ID.

    Parameters
    ----------
    content_id
        The ID of the content to retrieve.
    workspace_name
        The name of the workspace to retrieve content from.
    exclude_archived
        Specifies whether to exclude archived contents.
    exclude_unvalidated
        Specifies whether to exclude unvalidated contents.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    ContentRetrieve
        The retrieved content.

    Raises
    ------
    HTTPException
        If the content is not found.
    """
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    record = await get_content_from_db(
        asession=asession,
        content_id=content_id,
        exclude_archived=exclude_archived,
        exclude_unvalidated=exclude_unvalidated,
        workspace_id=workspace_db.workspace_id,
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content ID `{content_id}` not found",
        )

    return _convert_record_to_schema(record=record)


@router.post("/csv-upload", response_model=BulkUploadResponse)
async def bulk_upload_contents(
    file: UploadFile,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    exclude_archived: bool = True,
    exclude_unvalidated: bool = True,
    asession: AsyncSession = Depends(get_async_session),
) -> BulkUploadResponse:
    """Upload, check, and ingest contents in bulk from a CSV file.

    Note: If there are any issues with the CSV, the endpoint will return a 400 error
    with the list of issues under 'detail' in the response body.

    Parameters
    ----------
    file
        The CSV file to upload.
    calling_user_db
        The user object associated with the user that is uploading the CSV.
    workspace_name
        The name of the workspace to upload the contents to.
    exclude_archived
        Specifies whether to exclude archived contents.
    exclude_unvalidated
        Specifies whether to exclude unvalidated contents.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    BulkUploadResponse
        The response containing the created tags and contents.

    Raises
    ------
    HTTPException
        If the user does not have the required role to upload content in the workspace.
        If the file is not a CSV.
        If the CSV file is empty or unreadable.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to upload content in the "
            "workspace.",
        )

    # Ensure the file is a CSV.
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

    df = _load_csv(file=file)
    workspace_id = workspace_db.workspace_id
    await _csv_checks(asession=asession, df=df, workspace_id=workspace_id)

    # Create each new tag in the database.
    tags_col = "tags"
    created_tags: list[TagRetrieve] = []
    tag_name_to_id_map: dict[str, int] = {}
    skip_tags = tags_col not in df.columns or df[tags_col].isnull().all()
    if not skip_tags:
        incoming_tags = _extract_unique_tags(tags_col=df[tags_col])
        tags_in_db = await get_list_of_tag_from_db(
            asession=asession, workspace_id=workspace_id
        )
        tags_to_create = _get_tags_not_in_db(
            incoming_tags=incoming_tags, tags_in_db=tags_in_db
        )
        for tag in tags_to_create:
            tag_create = TagCreate(tag_name=tag)
            tag_db = await save_tag_to_db(
                asession=asession, tag=tag_create, workspace_id=workspace_id
            )
            tags_in_db.append(tag_db)

            # Convert the tag record to a schema (for response).
            tag_retrieve = _convert_tag_record_to_schema(record=tag_db)
            created_tags.append(tag_retrieve)

        # Tag name to tag ID mapping.
        tag_name_to_id_map = {tag.tag_name: tag.tag_id for tag in tags_in_db}

    # Add each row to the content database.
    created_contents = []
    for _, row in df.iterrows():
        content_tags: list = []  # Should be list[TagDB] but clashes with validate_tags
        if tag_name_to_id_map and not pd.isna(row[tags_col]):
            tag_names = [
                tag_name.strip().upper() for tag_name in row[tags_col].split(",")
            ]
            tag_ids = [tag_name_to_id_map[tag_name] for tag_name in tag_names]
            _, content_tags = await validate_tags(
                asession=asession, tags=tag_ids, workspace_id=workspace_id
            )

        content = ContentCreate(
            content_tags=content_tags,
            content_text=row["text"],
            content_title=row["title"],
            content_metadata={},
            related_contents_id=[],
        )

        content_db = await save_content_to_db(
            asession=asession,
            content=content,
            exclude_archived=exclude_archived,
            workspace_id=workspace_id,
        )
        content_retrieve = _convert_record_to_schema(record=content_db)
        created_contents.append(content_retrieve)

    return BulkUploadResponse(tags=created_tags, contents=created_contents)


def _load_csv(*, file: UploadFile) -> pd.DataFrame:
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
    *,
    asession: AsyncSession,
    error_list: list[CustomError],
    n_contents_to_add: int,
    workspace_id: int,
) -> None:
    """Check if the user would exceed their content quota given the number of new
    contents to add.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    error_list
        The list of errors to append to.
    n_contents_to_add
        The number of new contents to add.
    workspace_id
        The ID of the workspace to check the content quota for.
    """

    try:
        await _check_content_quota_availability(
            asession=asession,
            n_contents_to_add=n_contents_to_add,
            workspace_id=workspace_id,
        )
    except ExceedsContentQuotaError as e:
        error_list.append(CustomError(type="exceeds_quota", description=str(e)))


async def check_db_duplicates(
    *,
    asession: AsyncSession,
    df: pd.DataFrame,
    error_list: list[CustomError],
    workspace_id: int,
) -> None:
    """Check for duplicates between the CSV and the database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    df
        The DataFrame to check.
    error_list
        The list of errors to append to.
    workspace_id
        The ID of the workspace to check for content duplicates in.
    """

    contents_in_db = await get_list_of_content_from_db(
        asession=asession, limit=None, offset=0, workspace_id=workspace_id
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


async def _csv_checks(
    *, asession: AsyncSession, df: pd.DataFrame, workspace_id: int
) -> None:
    """Perform checks on the CSV file to ensure it meets the requirements.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    df
        The DataFrame to check.
    workspace_id
        The ID of the workspace that the CSV contents are being uploaded to.

    Raises
    ------
    HTTPException
        If the CSV file does not meet the requirements.
    """

    error_list: list[CustomError] = []
    check_required_columns(df=df, error_list=error_list)
    await check_content_quota(
        asession=asession,
        error_list=error_list,
        n_contents_to_add=len(df),
        workspace_id=workspace_id,
    )
    clean_dataframe(df=df)
    check_empty_values(df=df, error_list=error_list)
    check_length_constraints(df=df, error_list=error_list)
    check_duplicates(df=df, error_list=error_list)
    await check_db_duplicates(
        asession=asession, df=df, error_list=error_list, workspace_id=workspace_id
    )

    if error_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=CustomErrorList(errors=error_list).model_dump(),
        )


def check_duplicates(*, df: pd.DataFrame, error_list: list[CustomError]) -> None:
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


def check_empty_values(*, df: pd.DataFrame, error_list: list[CustomError]) -> None:
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


def check_length_constraints(
    *, df: pd.DataFrame, error_list: list[CustomError]
) -> None:
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


def check_required_columns(*, df: pd.DataFrame, error_list: list[CustomError]) -> None:
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


def clean_dataframe(*, df: pd.DataFrame) -> None:
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
    *, asession: AsyncSession, n_contents_to_add: int, workspace_id: int
) -> None:
    """Raise an error if the workspace would reach its content quota given N new
    contents.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    n_contents_to_add
        The number of new contents to add.
    workspace_id
        The ID of the workspace to check the content quota for.

    Raises
    ------
    ExceedsContentQuotaError
        If the workspace would exceed its content quota.
    """

    # Get the content quota value for the workspace from `WorkspaceDB`.
    content_quota = await get_content_quota_by_workspace_id(
        asession=asession, workspace_id=workspace_id
    )

    # If `content_quota` is `None`, then there is no limit.
    if content_quota is not None:
        # Get the number of contents already used by the workspace. This is all the
        # contents that have been added by users (i.e., admins) of the workspace.
        stmt = select(ContentDB).where(
            (ContentDB.workspace_id == workspace_id) & (~ContentDB.is_archived)
        )
        workspace_active_contents = (await asession.execute(stmt)).all()
        n_contents_in_workspace_db = len(workspace_active_contents)

        # Error if total of existing and new contents exceeds the quota.
        if (n_contents_in_workspace_db + n_contents_to_add) > content_quota:
            if n_contents_in_workspace_db > 0:
                raise ExceedsContentQuotaError(
                    f"Adding {n_contents_to_add} new contents to the already existing "
                    f"{n_contents_in_workspace_db} in the database would exceed the "
                    f"allowed limit of {content_quota} contents."
                )
            raise ExceedsContentQuotaError(
                f"Adding {n_contents_to_add} new contents to the database would "
                f"exceed the allowed limit of {content_quota} contents."
            )


def _extract_unique_tags(*, tags_col: pd.Series) -> list[str]:
    """Get unique UPPERCASE tags from a DataFrame column (comma-separated within
    column).

    Parameters
    ----------
    tags_col
        The column containing tags.

    Returns
    -------
    list[str]
        A list of unique tags.
    """

    # Prep the column.
    tags_col = tags_col.dropna().astype(str)

    # Split and explode to have one tag per row.
    tags_flat = tags_col.str.split(",").explode()

    # Strip and uppercase.
    tags_flat = tags_flat.str.strip().str.upper()

    # Get unique tags as a list.
    tags_unique_list = list(tags_flat.unique())

    return tags_unique_list


def _get_tags_not_in_db(
    *, incoming_tags: list[str], tags_in_db: list[TagDB]
) -> list[str]:
    """Compare tags fetched from the DB with incoming tags and return tags not in the
    DB.

    Parameters
    ----------
    incoming_tags
        List of incoming tags.
    tags_in_db
        List of `TagDB` objects fetched from the database.

    Returns
    -------
    list[str]
        List of tags not in the database.
    """

    tags_in_db_list: list[str] = [tag_json.tag_name for tag_json in tags_in_db]
    tags_not_in_db_list: list[str] = list(set(incoming_tags) - set(tags_in_db_list))

    return tags_not_in_db_list


def _convert_record_to_schema(*, record: ContentDB) -> ContentRetrieve:
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
        content_metadata=record.content_metadata,
        content_tags=[tag.tag_id for tag in record.content_tags],
        content_text=record.content_text,
        content_title=record.content_title,
        created_datetime_utc=record.created_datetime_utc,
        display_number=record.display_number,
        is_archived=record.is_archived,
        negative_votes=record.negative_votes,
        positive_votes=record.positive_votes,
        related_contents_id=record.related_contents_id,
        updated_datetime_utc=record.updated_datetime_utc,
        workspace_id=record.workspace_id,
    )

    return content_retrieve


def _convert_tag_record_to_schema(*, record: TagDB) -> TagRetrieve:
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
        created_datetime_utc=record.created_datetime_utc,
        tag_id=record.tag_id,
        tag_name=record.tag_name,
        updated_datetime_utc=record.updated_datetime_utc,
        workspace_id=record.workspace_id,
    )

    return tag_retrieve
