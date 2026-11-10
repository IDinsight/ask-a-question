"""This module contains FastAPI routers for tag management endpoints."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user, get_current_workspace_name
from app.core.database import get_async_session
from app.tags import service
from app.tags.schemas import TagCreate, TagRetrieve
from app.users.models import UserDB

TAG_METADATA = {
    "name": "Tag management for contents",
    "description": "_Requires user login._ Manage tags for content used "
    "for question answering.",
}

router = APIRouter(prefix="/tag", tags=[TAG_METADATA["name"]])


@router.post("/", response_model=TagRetrieve)
async def create_tag(
    tag: TagCreate,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> TagRetrieve:
    """Create a new tag.

    Parameters
    ----------
    tag:
        The tag to be created.
    calling_user_db
        The user object associated with the user that is creating the tag.
    workspace_name
        The name of the workspace to which the tag belongs.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    TagRetrieve
        The newly created tag.

    Raises
    ------
    HTTPException
        If the user does not have the required role to create tags in the workspace.
        If the tag name already exists.
    """

    return await service.create_tag(
        asession=asession,
        calling_user_db=calling_user_db,
        tag=tag,
        workspace_name=workspace_name,
    )


@router.put("/{tag_id}", response_model=TagRetrieve)
async def edit_tag(
    tag_id: int,
    tag: TagCreate,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> TagRetrieve:
    """Edit a pre-existing tag.

    Parameters
    ----------
    tag_id
        The ID of the tag to be edited.
    tag
        The new tag information.
    calling_user_db
        The user object associated with the user that is editing the tag.
    workspace_name
        The naem of the workspace to which the tag belongs.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    TagRetrieve
        The updated tag.

    Raises
    ------
    HTTPException
        If the user does not have the required role to edit tags in the workspace.
        If the tag ID is not found or the tag name already exists.
    """

    return await service.edit_tag(
        asession=asession,
        calling_user_db=calling_user_db,
        tag=tag,
        tag_id=tag_id,
        workspace_name=workspace_name,
    )


@router.get("/", response_model=list[TagRetrieve])
async def retrieve_tag(
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    skip: int = 0,
    limit: Optional[int] = None,
    asession: AsyncSession = Depends(get_async_session),
) -> list[TagRetrieve]:
    """Retrieve all tags in the workspace.

    Parameters
    ----------
    workspace_name
        The name of the workspace to retrieve tags from.
    skip
        The number of records to skip.
    limit
        The maximum number of records to retrieve.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[TagRetrieve]
        The list of tags in the workspace.
    """

    return await service.retrieve_tag(
        asession=asession, limit=limit, skip=skip, workspace_name=workspace_name
    )


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete tag by ID.

    Parameters
    ----------
    tag_id
        The ID of the tag to be deleted.
    calling_user_db
        The user object associated with the user that is deleting the tag.
    workspace_name
        The name of the workspace to which the tag belongs.
    asession
        The SQLAlchemy async session to use for all database connections.

    Raises
    ------
    HTTPException
        If the user does not have the required role to delete tags in the workspace.
        If the tag ID is not found.
    """

    await service.delete_tag(
        asession=asession,
        calling_user_db=calling_user_db,
        tag_id=tag_id,
        workspace_name=workspace_name,
    )


@router.get("/{tag_id}", response_model=TagRetrieve)
async def retrieve_tag_by_id(
    tag_id: int,
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> TagRetrieve:
    """Retrieve a tag by ID.

    Parameters
    ----------
    tag_id
        The ID of the tag to retrieve.
    workspace_name
        The name of the workspace to which the tag belongs.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    TagRetrieve
        The tag retrieved.

    Raises
    ------
    HTTPException
        If the tag ID is not found.
    """

    return await service.retrieve_tag_by_id(
        asession=asession, tag_id=tag_id, workspace_name=workspace_name
    )
