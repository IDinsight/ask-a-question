"""This module contains FastAPI routers for content management endpoints."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, UploadFile
from langfuse.decorators import observe  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user, get_current_workspace_name
from app.contents import service
from app.contents.schemas import BulkUploadResponse, ContentCreate, ContentRetrieve
from app.core.database import get_async_session
from app.users.models import UserDB

TAG_METADATA = {
    "name": "Content management",
    "description": "_Requires user login._ Manage content and tags to be used for "
    "question answering.",
}

router = APIRouter(prefix="/content", tags=[TAG_METADATA["name"]])


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

    return await service.create_content(
        asession=asession,
        calling_user_db=calling_user_db,
        content=content,
        workspace_name=workspace_name,
    )


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

    return await service.edit_content(
        asession=asession,
        calling_user_db=calling_user_db,
        content=content,
        content_id=content_id,
        exclude_archived=exclude_archived,
        exclude_unvalidated=exclude_unvalidated,
        workspace_name=workspace_name,
    )


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

    return await service.retrieve_content(
        asession=asession,
        exclude_archived=exclude_archived,
        exclude_unvalidated=exclude_unvalidated,
        limit=limit,
        skip=skip,
        workspace_name=workspace_name,
    )


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

    return await service.get_next_unvalidated_content(
        asession=asession,
        calling_user_db=calling_user_db,
        workspace_name=workspace_name,
    )


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

    await service.validate_content_card(
        asession=asession,
        calling_user_db=calling_user_db,
        content_id=content_id,
        workspace_name=workspace_name,
    )


@router.get("/unvalidated-count")
async def get_unvalidated_card_count(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> int:
    return await service.get_unvalidated_card_count(
        asession=asession,
        calling_user_db=calling_user_db,
        workspace_name=workspace_name,
    )


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

    await service.archive_content(
        asession=asession,
        calling_user_db=calling_user_db,
        content_id=content_id,
        exclude_unvalidated=exclude_unvalidated,
        workspace_name=workspace_name,
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

    await service.delete_content(
        asession=asession,
        calling_user_db=calling_user_db,
        content_id=content_id,
        exclude_archived=exclude_archived,
        exclude_unvalidated=exclude_unvalidated,
        workspace_name=workspace_name,
    )


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

    return await service.retrieve_content_by_id(
        asession=asession,
        content_id=content_id,
        exclude_archived=exclude_archived,
        exclude_unvalidated=exclude_unvalidated,
        workspace_name=workspace_name,
    )


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

    # Pass the underlying binary file object so the service stays FastAPI-free.
    return await service.bulk_upload_contents(
        asession=asession,
        calling_user_db=calling_user_db,
        exclude_archived=exclude_archived,
        file=file.file,
        filename=file.filename,
        workspace_name=workspace_name,
    )
