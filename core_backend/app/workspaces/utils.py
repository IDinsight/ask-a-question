"""This module contains utility functions for workspaces."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from ..users.models import WorkspaceDB
from ..users.schemas import UserCreate, UserRoles
from ..utils import get_key_hash
from .schemas import WorkspaceUpdate


class IncorrectUserRoleError(Exception):
    """Exception raised when the user role is incorrect."""


class WorkspaceNotFoundError(Exception):
    """Exception raised when a workspace is not found in the database."""


async def check_if_workspaces_exist(*, asession: AsyncSession) -> bool:
    """Check if workspaces exist in the `WorkspaceDB` database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    bool
        Specifies whether workspaces exists in the `WorkspaceDB` database.
    """

    stmt = select(WorkspaceDB.workspace_id).limit(1)
    result = await asession.scalars(stmt)
    return result.first() is not None


async def create_workspace(
    *,
    api_daily_quota: Optional[int] = None,
    asession: AsyncSession,
    content_quota: Optional[int] = None,
    user: UserCreate,
) -> WorkspaceDB:
    """Create a workspace in the `WorkspaceDB` database. If the workspace already
    exists, then it is returned.

    Parameters
    ----------
    api_daily_quota
        The daily API quota for the workspace.
    asession
        The SQLAlchemy async session to use for all database connections.
    content_quota
        The content quota for the workspace.
    user
        The user object creating the workspace.

    Returns
    -------
    WorkspaceDB
        The workspace object saved in the database.

    Raises
    ------
    IncorrectUserRoleError
        If the user role is incorrect for creating a workspace.
    """

    if user.role != UserRoles.ADMIN:
        raise IncorrectUserRoleError(
            f"Only {UserRoles.ADMIN} users can create workspaces."
        )

    result = await asession.execute(
        select(WorkspaceDB).where(WorkspaceDB.workspace_name == user.workspace_name)
    )
    workspace_db = result.scalar_one_or_none()
    if workspace_db is None:
        workspace_db = WorkspaceDB(
            api_daily_quota=api_daily_quota,
            content_quota=content_quota,
            created_datetime_utc=datetime.now(timezone.utc),
            updated_datetime_utc=datetime.now(timezone.utc),
            workspace_name=user.workspace_name,
        )

        asession.add(workspace_db)
        await asession.commit()
        await asession.refresh(workspace_db)

    return workspace_db


async def get_content_quota_by_workspace_id(
    *, asession: AsyncSession, workspace_id: int
) -> int:
    """Retrieve a workspace content quota by workspace ID.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_id
        The workspace ID to retrieve the content quota for.

    Returns
    -------
    int
        The content quota for the workspace.

    Raises
    ------
    WorkspaceNotFoundError
        If the workspace ID does not exist.
    """

    stmt = select(WorkspaceDB.content_quota).where(
        WorkspaceDB.workspace_id == workspace_id
    )
    result = await asession.execute(stmt)
    try:
        content_quota = result.scalar_one()
        return content_quota
    except NoResultFound as err:
        raise WorkspaceNotFoundError(
            f"Workspace ID {workspace_id} does not exist."
        ) from err


async def get_workspace_by_workspace_id(
    *, asession: AsyncSession, workspace_id: int
) -> WorkspaceDB:
    """Retrieve a workspace by workspace ID.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_id
        The workspace ID to use for the query.

    Returns
    -------
    WorkspaceDB
        The workspace object retrieved from the database.

    Raises
    ------
    WorkspaceNotFoundError
        If the workspace with the specified workspace ID does not exist.
    """

    stmt = select(WorkspaceDB).where(WorkspaceDB.workspace_id == workspace_id)
    result = await asession.execute(stmt)
    try:
        workspace_db = result.scalar_one()
        return workspace_db
    except NoResultFound as err:
        raise WorkspaceNotFoundError(
            f"Workspace with ID {workspace_id} does not exist."
        ) from err


async def get_workspace_by_workspace_name(
    *, asession: AsyncSession, workspace_name: str
) -> WorkspaceDB:
    """Retrieve a workspace by workspace name.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_name
        The workspace name to use for the query.

    Returns
    -------
    WorkspaceDB
        The workspace object retrieved from the database.

    Raises
    ------
    WorkspaceNotFoundError
        If the workspace with the specified workspace name does not exist.
    """

    stmt = select(WorkspaceDB).where(WorkspaceDB.workspace_name == workspace_name)
    result = await asession.execute(stmt)
    try:
        workspace_db = result.scalar_one()
        return workspace_db
    except NoResultFound as err:
        raise WorkspaceNotFoundError(
            f"Workspace with name {workspace_name} does not exist."
        ) from err


async def update_workspace_api_key(
    *, asession: AsyncSession, new_api_key: str, workspace_db: WorkspaceDB
) -> WorkspaceDB:
    """Update a workspace API key.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    new_api_key
        The new API key to update.
    workspace_db
        The workspace object to update the API key for.

    Returns
    -------
    WorkspaceDB
        The workspace object updated in the database after API key update.
    """

    workspace_db.hashed_api_key = get_key_hash(new_api_key)
    workspace_db.api_key_first_characters = new_api_key[:5]
    workspace_db.api_key_updated_datetime_utc = datetime.now(timezone.utc)
    workspace_db.updated_datetime_utc = datetime.now(timezone.utc)

    await asession.commit()
    await asession.refresh(workspace_db)

    return workspace_db


async def update_workspace_quotas(
    *, asession: AsyncSession, workspace: WorkspaceUpdate, workspace_db: WorkspaceDB
) -> WorkspaceDB:
    """Update workspace quotas.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace
        The workspace object containing the updated quotas.
    workspace_db
        The workspace object to update the API key for.

    Returns
    -------
    WorkspaceDB
        The workspace object updated in the database after updating quotas.
    """

    assert workspace.api_daily_quota is None or workspace.api_daily_quota >= 0
    assert workspace.content_quota is None or workspace.content_quota >= 0
    workspace_db.api_daily_quota = workspace.api_daily_quota
    workspace_db.content_quota = workspace.content_quota
    workspace_db.updated_datetime_utc = datetime.now(timezone.utc)

    await asession.commit()
    await asession.refresh(workspace_db)

    return workspace_db
