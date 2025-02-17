"""This module contains FastAPI routers for tag management endpoints."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_workspace_name
from ..database import get_async_session
from ..users.models import UserDB, user_has_required_role_in_workspace
from ..users.schemas import UserRoles
from ..utils import setup_logger
from ..workspaces.utils import get_workspace_by_workspace_name
from .models import (
    TagDB,
    delete_tag_from_db,
    get_list_of_tag_from_db,
    get_tag_from_db,
    is_tag_name_unique,
    save_tag_to_db,
    update_tag_in_db,
)
from .schemas import TagCreate, TagRetrieve

TAG_METADATA = {
    "name": "Tag management for contents",
    "description": "_Requires user login._ Manage tags for content used "
    "for question answering.",
}

router = APIRouter(prefix="/tag", tags=[TAG_METADATA["name"]])
logger = setup_logger()


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
            detail="User does not have the required role to create tags in the "
            "workspace.",
        )

    tag.tag_name = tag.tag_name.upper()
    if not await is_tag_name_unique(
        asession=asession, tag_name=tag.tag_name, workspace_id=workspace_db.workspace_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tag name `{tag.tag_name}` already exists",
        )
    tag_db = await save_tag_to_db(
        asession=asession, tag=tag, workspace_id=workspace_db.workspace_id
    )
    return _convert_record_to_schema(record=tag_db)


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
            detail="User does not have the required role to edit tags in the "
            "workspace.",
        )

    tag.tag_name = tag.tag_name.upper()
    old_tag = await get_tag_from_db(
        asession=asession, tag_id=tag_id, workspace_id=workspace_db.workspace_id
    )

    if not old_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tag ID `{tag_id}` not found"
        )
    assert isinstance(old_tag, TagDB)

    if (tag.tag_name != old_tag.tag_name) and not (
        await is_tag_name_unique(
            asession=asession,
            tag_name=tag.tag_name,
            workspace_id=workspace_db.workspace_id,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tag name `{tag.tag_name}` already exists",
        )

    updated_tag = await update_tag_in_db(
        asession=asession,
        tag=tag,
        tag_id=tag_id,
        workspace_id=workspace_db.workspace_id,
    )

    return _convert_record_to_schema(record=updated_tag)


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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    records = await get_list_of_tag_from_db(
        asession=asession,
        limit=limit,
        offset=skip,
        workspace_id=workspace_db.workspace_id,
    )
    tags = [_convert_record_to_schema(record=c) for c in records]
    return tags


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
            detail="User does not have the required role to delete tags in the "
            "workspace.",
        )

    record = await get_tag_from_db(
        asession=asession, tag_id=tag_id, workspace_id=workspace_db.workspace_id
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tag ID `{tag_id}` not found"
        )

    await delete_tag_from_db(
        asession=asession, tag_id=tag_id, workspace_id=workspace_db.workspace_id
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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    record = await get_tag_from_db(
        asession=asession, tag_id=tag_id, workspace_id=workspace_db.workspace_id
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tag ID `{tag_id}` not found"
        )

    assert isinstance(record, TagDB)
    return _convert_record_to_schema(record=record)


def _convert_record_to_schema(*, record: TagDB) -> TagRetrieve:
    """Convert `models.TagDB` models to `TagRetrieve` schema.

    Parameters
    ----------
    record
        The tag record to convert.

    Returns
    -------
    TagRetrieve
        The converted tag record.
    """

    tag_retrieve = TagRetrieve(
        created_datetime_utc=record.created_datetime_utc,
        tag_id=record.tag_id,
        tag_name=record.tag_name,
        updated_datetime_utc=record.updated_datetime_utc,
        workspace_id=record.workspace_id,
    )

    return tag_retrieve
