"""Business logic for tag management.

Route handlers in `app.tags.router` delegate here. Functions in this module raise
the domain exceptions from `app.core.exceptions` (never `HTTPException`).
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.tags.models import TagDB
from app.tags.repository import (
    delete_tag_from_db,
    get_list_of_tag_from_db,
    get_tag_from_db,
    is_tag_name_unique,
    save_tag_to_db,
    update_tag_in_db,
)
from app.tags.schemas import TagCreate, TagRetrieve
from app.users.models import UserDB
from app.users.repository import user_has_required_role_in_workspace
from app.users.schemas import UserRoles
from app.workspaces.models import WorkspaceDB
from app.workspaces.repository import get_workspace_by_workspace_name


async def _get_workspace_as_admin(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    forbidden_detail: str,
    workspace_name: str,
) -> WorkspaceDB:
    """Fetch the workspace and ensure the calling user is an admin in it.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user making the request.
    forbidden_detail
        The error detail to return if the user is not an admin in the workspace.
    workspace_name
        The name of the workspace.

    Returns
    -------
    WorkspaceDB
        The workspace object.

    Raises
    ------
    ForbiddenError
        If the user does not have the admin role in the workspace.
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
        raise ForbiddenError(forbidden_detail)

    return workspace_db


async def create_tag(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    tag: TagCreate,
    workspace_name: str,
) -> TagRetrieve:
    """Create a new tag in the workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is creating the tag.
    tag
        The tag to be created. Its name is upper-cased in place.
    workspace_name
        The name of the workspace to which the tag belongs.

    Returns
    -------
    TagRetrieve
        The newly created tag.

    Raises
    ------
    ForbiddenError
        If the user does not have the required role to create tags in the workspace.
    BadRequestError
        If the tag name already exists.
    """

    workspace_db = await _get_workspace_as_admin(
        asession=asession,
        calling_user_db=calling_user_db,
        forbidden_detail="User does not have the required role to create tags in the "
        "workspace.",
        workspace_name=workspace_name,
    )

    # Tag names are stored upper-case so that uniqueness is case-insensitive.
    tag.tag_name = tag.tag_name.upper()
    if not await is_tag_name_unique(
        asession=asession, tag_name=tag.tag_name, workspace_id=workspace_db.workspace_id
    ):
        raise BadRequestError(f"Tag name `{tag.tag_name}` already exists")
    tag_db = await save_tag_to_db(
        asession=asession, tag=tag, workspace_id=workspace_db.workspace_id
    )
    return _convert_record_to_schema(record=tag_db)


async def edit_tag(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    tag: TagCreate,
    tag_id: int,
    workspace_name: str,
) -> TagRetrieve:
    """Edit a pre-existing tag.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is editing the tag.
    tag
        The new tag information. Its name is upper-cased in place.
    tag_id
        The ID of the tag to be edited.
    workspace_name
        The name of the workspace to which the tag belongs.

    Returns
    -------
    TagRetrieve
        The updated tag.

    Raises
    ------
    ForbiddenError
        If the user does not have the required role to edit tags in the workspace.
    NotFoundError
        If the tag ID is not found.
    BadRequestError
        If the new tag name already exists.
    """

    workspace_db = await _get_workspace_as_admin(
        asession=asession,
        calling_user_db=calling_user_db,
        forbidden_detail="User does not have the required role to edit tags in the "
        "workspace.",
        workspace_name=workspace_name,
    )

    tag.tag_name = tag.tag_name.upper()
    old_tag = await get_tag_from_db(
        asession=asession, tag_id=tag_id, workspace_id=workspace_db.workspace_id
    )

    if not old_tag:
        raise NotFoundError(f"Tag ID `{tag_id}` not found")
    assert isinstance(old_tag, TagDB)

    # Only check uniqueness when the name actually changes.
    if (tag.tag_name != old_tag.tag_name) and not (
        await is_tag_name_unique(
            asession=asession,
            tag_name=tag.tag_name,
            workspace_id=workspace_db.workspace_id,
        )
    ):
        raise BadRequestError(f"Tag name `{tag.tag_name}` already exists")

    updated_tag = await update_tag_in_db(
        asession=asession,
        tag=tag,
        tag_id=tag_id,
        workspace_id=workspace_db.workspace_id,
    )

    return _convert_record_to_schema(record=updated_tag)


async def retrieve_tag(
    *,
    asession: AsyncSession,
    limit: Optional[int],
    skip: int,
    workspace_name: str,
) -> list[TagRetrieve]:
    """Retrieve all tags in the workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    limit
        The maximum number of records to retrieve.
    skip
        The number of records to skip.
    workspace_name
        The name of the workspace to retrieve tags from.

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
    return [_convert_record_to_schema(record=c) for c in records]


async def delete_tag(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    tag_id: int,
    workspace_name: str,
) -> None:
    """Delete tag by ID.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is deleting the tag.
    tag_id
        The ID of the tag to be deleted.
    workspace_name
        The name of the workspace to which the tag belongs.

    Raises
    ------
    ForbiddenError
        If the user does not have the required role to delete tags in the workspace.
    NotFoundError
        If the tag ID is not found.
    """

    workspace_db = await _get_workspace_as_admin(
        asession=asession,
        calling_user_db=calling_user_db,
        forbidden_detail="User does not have the required role to delete tags in the "
        "workspace.",
        workspace_name=workspace_name,
    )

    record = await get_tag_from_db(
        asession=asession, tag_id=tag_id, workspace_id=workspace_db.workspace_id
    )
    if not record:
        raise NotFoundError(f"Tag ID `{tag_id}` not found")

    await delete_tag_from_db(
        asession=asession, tag_id=tag_id, workspace_id=workspace_db.workspace_id
    )


async def retrieve_tag_by_id(
    *, asession: AsyncSession, tag_id: int, workspace_name: str
) -> TagRetrieve:
    """Retrieve a tag by ID.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    tag_id
        The ID of the tag to retrieve.
    workspace_name
        The name of the workspace to which the tag belongs.

    Returns
    -------
    TagRetrieve
        The tag retrieved.

    Raises
    ------
    NotFoundError
        If the tag ID is not found.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    record = await get_tag_from_db(
        asession=asession, tag_id=tag_id, workspace_id=workspace_db.workspace_id
    )
    if not record:
        raise NotFoundError(f"Tag ID `{tag_id}` not found")

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
