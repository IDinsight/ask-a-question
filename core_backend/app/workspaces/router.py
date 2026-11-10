"""This module contains FastAPI routers for workspace endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user, get_current_workspace_name
from app.auth.schemas import AuthenticationDetails
from app.core.database import get_async_session
from app.users.models import UserDB
from app.workspaces import service
from app.workspaces.schemas import (
    WorkspaceCreate,
    WorkspaceKeyResponse,
    WorkspaceRetrieve,
    WorkspaceSwitch,
    WorkspaceUpdate,
)

TAG_METADATA = {
    "name": "Workspace",
    "description": "_Requires user login._ Only administrator user has access to these "
    "endpoints and only for the workspaces that they are assigned to.",
}

router = APIRouter(prefix="/workspace", tags=["Workspace"])


@router.post("/", response_model=list[WorkspaceRetrieve])
async def create_workspaces(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspaces: WorkspaceCreate | list[WorkspaceCreate],
    asession: AsyncSession = Depends(get_async_session),
) -> list[WorkspaceRetrieve]:
    """Create workspaces. Workspaces can only be created by ADMIN users.

    NB: Any user is allowed to create a workspace. However, the user must be assigned
    to a default workspace already.

    NB: When a workspace is created, the API daily quota and content quota limits for
    the workspace is set to global defaults regardless of what the user specifies.

    The process is as follows:

    1. Create each workspace. If a workspace already exists during this process, an
        error is NOT thrown. Instead, the existing workspace object is NOT returned to
        the calling user. This avoids the need to iterate thru the list of workspaces
        first and does not give the calling user information on workspace existence.
    2. If a new workspace was created, then the calling user is automatically added as
        an ADMIN user to the workspace. Otherwise, the calling user is not added and
        they would have to contact the admin of the (existing) workspace to be added.
        2a. We do NOT assign the calling user to any of the newly created workspaces
        because existing users must already have a default workspace assigned and we
        don't want to override their current default workspace when creating new
        workspaces.

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
    list[WorkspaceRetrieve]
        A list of created workspace objects.

    Raises
    ------
    HTTPException
        If the calling user does not have a default workspace assigned
    """

    return await service.create_workspaces(
        asession=asession, calling_user_db=calling_user_db, workspaces=workspaces
    )


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

    return await service.retrieve_admin_workspaces(
        asession=asession, calling_user_db=calling_user_db
    )


@router.get("/current-workspace", response_model=WorkspaceRetrieve)
async def retrieve_current_workspace(
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> WorkspaceRetrieve:
    """Return the current workspace.

    NB: This endpoint can be called by any authenticated user.

    Parameters
    ----------
    workspace_name
        The name of the current workspace to retrieve.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    WorkspaceRetrieve
        The current workspace object.
    """

    return await service.retrieve_workspace_by_name(
        asession=asession, workspace_name=workspace_name
    )


@router.get("/{workspace_id}", response_model=WorkspaceRetrieve)
async def retrieve_workspace_by_workspace_id(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_id: int,
    asession: AsyncSession = Depends(get_async_session),
) -> WorkspaceRetrieve:
    """Retrieve a workspace by ID.

    NB: When this endpoint called, it **should** be called by ADMIN users only since
    details about a workspace are returned.

    The process is as follows:

    1. Only retrieve workspaces for which the calling user has an ADMIN role.
    2. If the calling user is an admin in the specified workspace, then the details for
        that workspace are returned.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user that is retrieving the workspace.
    workspace_id
        The workspace ID to retrieve.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    WorkspaceRetrieve
        The retrieved workspace object.

    Raises
    ------
    HTTPException
        If the calling user does not have the correct role to retrieve workspaces.
        If the calling user is not an admin in the specified workspace.
    """

    return await service.retrieve_admin_workspace_by_id(
        asession=asession, calling_user_db=calling_user_db, workspace_id=workspace_id
    )


@router.get("/get-user-workspaces/{user_id}", response_model=list[WorkspaceRetrieve])
async def retrieve_workspaces_by_user_id(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    user_id: int,
    asession: AsyncSession = Depends(get_async_session),
) -> list[WorkspaceRetrieve]:
    """Retrieve workspaces by user ID.

    NB: When this endpoint called, it **should** be called by ADMIN users only since
    details about workspaces are returned.

    The process is as follows:

    1. Only retrieve workspaces for which the calling user has an ADMIN role.
    2. If the calling user is an admin in the same workspace as the user, then details
        for that workspace are returned.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user that is retrieving the workspaces.
    user_id
        The user ID to retrieve workspaces for.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[WorkspaceRetrieve]
        A list of workspace objects that the user belongs to.

    Raises
    ------
    HTTPException
        If the calling user does not have the correct role to retrieve workspaces.
        If the user ID does not exist.
        If the calling user is not an admin in the same workspace as the user.
    """

    return await service.retrieve_user_workspaces_for_admin(
        asession=asession, calling_user_db=calling_user_db, user_id=user_id
    )


@router.put("/rotate-key", response_model=WorkspaceKeyResponse)
async def get_new_api_key(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> WorkspaceKeyResponse:
    """Generate a new API key for the workspace. Takes a workspace object, generates a
    new key, replaces the old one in the database, and returns a workspace object with
    the new key.

    NB: When this endpoint called, it **should** be called by ADMIN users only since a
    new API key is being requested for a workspace.

    The process is as follows:

    1. Only retrieve workspaces for which the calling user has an ADMIN role.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user requesting the new API key.
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
        If the calling user does not have the correct role to request a new API key for
        the workspace.
        If there is an error updating the workspace API key.
    """

    return await service.rotate_workspace_api_key(
        asession=asession,
        calling_user_db=calling_user_db,
        workspace_name=workspace_name,
    )


@router.post("/switch-workspace")
async def switch_workspace(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_switch: WorkspaceSwitch,
    asession: AsyncSession = Depends(get_async_session),
) -> AuthenticationDetails:
    """Switch to a different workspace.

    NB: A user should first be authenticated before they are allowed to switch to
    another workspace.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user switching workspaces.
    workspace_switch
        The workspace switch object containing the workspace name to switch into.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    AuthenticationDetails
        The authentication details object containing the new access token.

    Raises
    ------
    HTTPException
        If the workspace to switch into does not exist.
        If the calling user's role in the workspace to switch into is not valid.
    """

    return await service.switch_user_workspace(
        asession=asession,
        calling_user_db=calling_user_db,
        workspace_name=workspace_switch.workspace_name,
    )


@router.put("/{workspace_id}", response_model=WorkspaceUpdate)
async def update_workspace(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_id: int,
    workspace: WorkspaceUpdate,
    asession: AsyncSession = Depends(get_async_session),
) -> WorkspaceUpdate:
    """Update the name for an existing workspace. Only admin users can update workspace
    name and only for the workspaces that they are assigned to.

    NB: The ID for a workspace can NOT be updated since this would involve propagating
    user and roles changes as well. However, the workspace name can be changed
    (assuming it is unique).

    NB: Workspace quotas cannot be changed currently. These values are assigned to
    reasonable defaults when a workspace is created and are not meant to be changed
    except by the system administrator.

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
    WorkspaceUpdate
        The updated workspace object.

    Raises
    ------
    HTTPException
        If the workspace to update does not exist.
        If the calling user does not have the correct role to update the workspace.
        If there is an error updating the workspace quotas.
    """

    return await service.update_workspace(
        asession=asession,
        calling_user_db=calling_user_db,
        workspace=workspace,
        workspace_id=workspace_id,
    )
