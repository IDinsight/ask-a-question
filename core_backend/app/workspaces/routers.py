"""This module contains FastAPI routers for workspace endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_workspace_name
from ..database import get_async_session
from ..users.models import (
    UserDB,
    UserNotFoundError,
    get_user_by_id,
    get_user_role_in_workspace,
    get_user_workspaces,
    get_workspaces_by_user_role,
    user_has_admin_role_in_any_workspace,
)
from ..users.schemas import UserCreate, UserRoles
from ..utils import generate_key, setup_logger
from .schemas import (
    WorkspaceCreate,
    WorkspaceKeyResponse,
    WorkspaceQuotaResponse,
    WorkspaceRetrieve,
    WorkspaceUpdate,
)
from .utils import (
    WorkspaceNotFoundError,
    create_workspace,
    get_workspace_by_workspace_id,
    get_workspace_by_workspace_name,
    update_workspace_api_key,
    update_workspace_quotas,
)

TAG_METADATA = {
    "name": "Workspace",
    "description": "_Requires user login._ Only administrator user has access to these "
    "endpoints and only for the workspaces that they are assigned to.",
}

router = APIRouter(prefix="/workspace", tags=["Workspace"])
logger = setup_logger()


@router.post("/", response_model=list[WorkspaceCreate])
async def create_workspaces(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspaces: WorkspaceCreate | list[WorkspaceCreate],
    asession: AsyncSession = Depends(get_async_session),
) -> list[WorkspaceCreate]:
    """Create workspaces. Workspaces can only be created by ADMIN users.

    NB: When a workspace is created, the API daily quota and content quota limits for
    the workspace is set.

    The process is as follows:

    1. If the calling user does not have the correct role to create workspaces, then an
        error is thrown.
    2. Create each workspace. If a workspace already exists during this process, an
        error is NOT thrown. Instead, the existing workspace object is returned. This
        avoids the need to iterate thru the list of workspaces first.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user that is creating the workspace(s).
    workspaces
        The list of workspace objects to create.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[WorkspaceCreate]
        A list of created workspace objects.

    Raises
    ------
    HTTPException
        If the calling user does not have the correct role to create workspaces.
    """

    # 1.
    if not await user_has_admin_role_in_any_workspace(
        asession=asession, user_db=calling_user_db
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calling user does not have the correct role to create workspaces.",
        )

    # 2.
    if not isinstance(workspaces, list):
        workspaces = [workspaces]
    workspace_dbs = [
        await create_workspace(
            api_daily_quota=workspace.api_daily_quota,
            asession=asession,
            content_quota=workspace.content_quota,
            user=UserCreate(
                role=UserRoles.ADMIN,
                username=calling_user_db.username,
                workspace_name=workspace.workspace_name,
            ),
        )
        for workspace in workspaces
    ]
    return [
        WorkspaceCreate(
            api_daily_quota=workspace_db.api_daily_quota,
            content_quota=workspace_db.content_quota,
            workspace_name=workspace_db.workspace_name,
        )
        for workspace_db in workspace_dbs
    ]


@router.get("/", response_model=list[WorkspaceRetrieve])
async def retrieve_all_workspaces(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[WorkspaceRetrieve]:
    """Return a list of all workspaces.

    NB: When this endpoint called, it **should** be called by ADMIN users only since
    details about workspaces are returned.

    The process is as follows:

    1. Only retrieve workspaces for which the calling user has an ADMIN role.
    2. If the calling user is an admin in a workspace, then the details for that
        workspace are returned.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user that is retrieving the list of
        workspaces.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[WorkspaceRetrieve]
        A list of retrieved workspace objects.

    Raises
    ------
    HTTPException
        If the calling user does not have the correct role to retrieve workspaces.
    """

    if not await user_has_admin_role_in_any_workspace(
        asession=asession, user_db=calling_user_db
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calling user does not have the correct role to retrieve "
            "workspaces.",
        )

    # 1.
    calling_user_admin_workspace_dbs = await get_workspaces_by_user_role(
        asession=asession, user_db=calling_user_db, user_role=UserRoles.ADMIN
    )

    # 2.
    return [
        WorkspaceRetrieve(
            api_daily_quota=workspace_db.api_daily_quota,
            api_key_first_characters=workspace_db.api_key_first_characters,
            api_key_updated_datetime_utc=workspace_db.api_key_updated_datetime_utc,
            content_quota=workspace_db.content_quota,
            created_datetime_utc=workspace_db.created_datetime_utc,
            updated_datetime_utc=workspace_db.updated_datetime_utc,
            workspace_id=workspace_db.workspace_id,
            workspace_name=workspace_db.workspace_name,
        )
        for workspace_db in calling_user_admin_workspace_dbs
    ]


@router.get("/{user_id}", response_model=list[WorkspaceRetrieve])
async def retrieve_workspaces_by_user_id(
    user_id: int, asession: AsyncSession = Depends(get_async_session)
) -> list[WorkspaceRetrieve]:
    """Retrieve workspaces by user ID. If the user does not exist or they do not belong
    to any workspaces, then an empty list is returned.

    Parameters
    ----------
    user_id
        The user ID to retrieve workspaces for.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[WorkspaceRetrieve]
        A list of workspace objects that the user belongs to.
    """

    try:
        user_db = await get_user_by_id(asession=asession, user_id=user_id)
    except UserNotFoundError:
        return []

    user_workspace_dbs = await get_user_workspaces(asession=asession, user_db=user_db)
    return [
        WorkspaceRetrieve(
            api_daily_quota=user_workspace_db.api_daily_quota,
            api_key_first_characters=user_workspace_db.api_key_first_characters,
            api_key_updated_datetime_utc=user_workspace_db.api_key_updated_datetime_utc,
            content_quota=user_workspace_db.content_quota,
            created_datetime_utc=user_workspace_db.created_datetime_utc,
            updated_datetime_utc=user_workspace_db.updated_datetime_utc,
            workspace_id=user_workspace_db.workspace_id,
            workspace_name=user_workspace_db.workspace_name,
        )
        for user_workspace_db in user_workspace_dbs
    ]


@router.put("/{workspace_id}", response_model=WorkspaceUpdate)
async def update_workspace(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_id: int,
    workspace: WorkspaceUpdate,
    asession: AsyncSession = Depends(get_async_session),
) -> WorkspaceQuotaResponse:
    """Update the quotas for an existing workspace. Only admin users can update
    workspace quotas and only for the workspaces that they are assigned to.

    NB: The ID for a workspace can NOT be updated since this would involve propagating
    user and roles changes as well. However, the workspace name can be changed
    (assuming it is unique).

    Parameters
    ----------
    calling_user_db
        The user object associated with the user updating the workspace.
    workspace_id
        The workspace ID to update.
    workspace
        The workspace object with the updated quotas.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    WorkspaceQuotaResponse
        The response object containing the new quotas.

    Raises
    ------
    HTTPException
        If the workspace to update does not exist.
        If the calling user does not have the correct role to update the workspace.
        If there is an error updating the workspace quotas.
    """

    try:
        workspace_db = await get_workspace_by_workspace_id(
            asession=asession, workspace_id=workspace_id
        )
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace ID {workspace_id} not found.",
        ) from e

    calling_user_workspace_role = get_user_role_in_workspace(
        asession=asession, user_db=calling_user_db, workspace_db=workspace_db
    )

    if calling_user_workspace_role != UserRoles.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Calling user is not an admin in the workspace.",
        )

    try:
        # This is necessary to attach the `workspace_db` object to the session.
        asession.add(workspace_db)
        workspace_db_updated = await update_workspace_quotas(
            asession=asession, workspace=workspace, workspace_db=workspace_db
        )
        return WorkspaceQuotaResponse(
            new_api_daily_quota=workspace_db_updated.api_daily_quota,
            new_content_quota=workspace_db_updated.content_quota,
            workspace_name=workspace_db_updated.workspace_name,
        )
    except SQLAlchemyError as e:
        logger.error(f"Error updating workspace quotas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating workspace quotas.",
        ) from e


@router.put("/rotate-key", response_model=WorkspaceKeyResponse)
async def get_new_api_key(
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> WorkspaceKeyResponse:
    """Generate a new API key for the workspace. Takes a workspace object, generates a
    new key, replaces the old one in the database, and returns a workspace object with
    the new key.

    Parameters
    ----------
    workspace_name
        The name of the workspace requesting the new API key.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    WorkspaceKeyResponse
        The response object containing the new API key.

    Raises
    ------
    HTTPException
        If there is an error updating the workspace API key.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    new_api_key = generate_key()

    try:
        # This is necessary to attach the `workspace_db` object to the session.
        asession.add(workspace_db)
        workspace_db_updated = await update_workspace_api_key(
            asession=asession, new_api_key=new_api_key, workspace_db=workspace_db
        )
        return WorkspaceKeyResponse(
            new_api_key=new_api_key, workspace_name=workspace_db_updated.workspace_name
        )
    except SQLAlchemyError as e:
        logger.error(f"Error updating workspace API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating workspace API key.",
        ) from e
