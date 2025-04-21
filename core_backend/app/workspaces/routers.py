"""This module contains FastAPI routers for workspace endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import (
    create_access_token,
    get_current_user,
    get_current_workspace_name,
)
from ..auth.schemas import AuthenticationDetails
from ..config import DEFAULT_API_QUOTA, DEFAULT_CONTENT_QUOTA
from ..database import get_async_session
from ..users.models import (
    UserDB,
    UserNotFoundError,
    WorkspaceDB,
    add_existing_user_to_workspace,
    check_if_user_has_default_workspace,
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
    WorkspaceRetrieve,
    WorkspaceSwitch,
    WorkspaceUpdate,
)
from .utils import (
    WorkspaceNotFoundError,
    create_workspace,
    get_workspace_by_workspace_id,
    get_workspace_by_workspace_name,
    is_workspace_name_valid,
    update_workspace_api_key,
    update_workspace_name_and_quotas,
)

TAG_METADATA = {
    "name": "Workspace",
    "description": "_Requires user login._ Only administrator user has access to these "
    "endpoints and only for the workspaces that they are assigned to.",
}

router = APIRouter(prefix="/workspace", tags=["Workspace"])
logger = setup_logger()


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

    if not await check_if_user_has_default_workspace(
        asession=asession, user_db=calling_user_db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Calling user must be assigned to a workspace first before creating "
            "workspaces.",
        )

    if not isinstance(workspaces, list):
        workspaces = [workspaces]
    created_workspaces: list[WorkspaceRetrieve] = []

    for workspace in workspaces:
        # 1.
        workspace_db, is_new_workspace = await create_workspace(
            api_daily_quota=DEFAULT_API_QUOTA,  # workspace.api_daily_quota,
            asession=asession,
            content_quota=DEFAULT_CONTENT_QUOTA,  # workspace.content_quota,
            user=UserCreate(
                role=UserRoles.ADMIN,
                username=calling_user_db.username,
                workspace_name=workspace.workspace_name,
            ),
        )

        # 2.
        if is_new_workspace:
            await add_existing_user_to_workspace(
                asession=asession,
                user=UserCreate(
                    is_default_workspace=False,  # 2a.
                    role=UserRoles.ADMIN,
                    username=calling_user_db.username,
                    workspace_name=workspace_db.workspace_name,
                ),
                workspace_db=workspace_db,
            )
            created_workspaces.append(
                WorkspaceRetrieve(
                    api_daily_quota=workspace_db.api_daily_quota,
                    api_key_first_characters=workspace_db.api_key_first_characters,
                    api_key_updated_datetime_utc=workspace_db.api_key_updated_datetime_utc,  # noqa: E501
                    content_quota=workspace_db.content_quota,
                    created_datetime_utc=workspace_db.created_datetime_utc,
                    updated_datetime_utc=workspace_db.updated_datetime_utc,
                    workspace_id=workspace_db.workspace_id,
                    workspace_name=workspace_db.workspace_name,
                )
            )

    return created_workspaces


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
            status_code=status.HTTP_403_FORBIDDEN,
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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    return WorkspaceRetrieve(
        api_daily_quota=workspace_db.api_daily_quota,
        api_key_first_characters=workspace_db.api_key_first_characters,
        api_key_updated_datetime_utc=workspace_db.api_key_updated_datetime_utc,
        content_quota=workspace_db.content_quota,
        created_datetime_utc=workspace_db.created_datetime_utc,
        updated_datetime_utc=workspace_db.updated_datetime_utc,
        workspace_id=workspace_db.workspace_id,
        workspace_name=workspace_db.workspace_name,
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

    if not await user_has_admin_role_in_any_workspace(
        asession=asession, user_db=calling_user_db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Calling user does not have the correct role to retrieve "
            "workspaces.",
        )

    # 1.
    calling_user_admin_workspace_dbs = await get_workspaces_by_user_role(
        asession=asession, user_db=calling_user_db, user_role=UserRoles.ADMIN
    )
    matched_workspace_db = next(
        (
            workspace_db
            for workspace_db in calling_user_admin_workspace_dbs
            if workspace_db.workspace_id == workspace_id
        ),
        None,
    )

    if matched_workspace_db is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Calling user is not an admin in the workspace.",
        )

    # 2.
    return WorkspaceRetrieve(
        api_daily_quota=matched_workspace_db.api_daily_quota,
        api_key_first_characters=matched_workspace_db.api_key_first_characters,
        api_key_updated_datetime_utc=matched_workspace_db.api_key_updated_datetime_utc,
        content_quota=matched_workspace_db.content_quota,
        created_datetime_utc=matched_workspace_db.created_datetime_utc,
        updated_datetime_utc=matched_workspace_db.updated_datetime_utc,
        workspace_id=matched_workspace_db.workspace_id,
        workspace_name=matched_workspace_db.workspace_name,
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

    if not await user_has_admin_role_in_any_workspace(
        asession=asession, user_db=calling_user_db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Calling user does not have the correct role to retrieve "
            "workspaces.",
        )

    try:
        user_db = await get_user_by_id(asession=asession, user_id=user_id)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User ID {user_id} not found.",
        ) from e

    # 1.
    calling_user_admin_workspace_dbs = await get_workspaces_by_user_role(
        asession=asession, user_db=calling_user_db, user_role=UserRoles.ADMIN
    )

    # 2.
    user_workspace_dbs = await get_user_workspaces(asession=asession, user_db=user_db)
    calling_user_admin_workspace_ids = [
        db.workspace_id for db in calling_user_admin_workspace_dbs
    ]

    retrieved_workspaces: list[WorkspaceRetrieve] = [
        WorkspaceRetrieve(
            api_daily_quota=db.api_daily_quota,
            api_key_first_characters=db.api_key_first_characters,
            api_key_updated_datetime_utc=db.api_key_updated_datetime_utc,
            content_quota=db.content_quota,
            created_datetime_utc=db.created_datetime_utc,
            updated_datetime_utc=db.updated_datetime_utc,
            workspace_id=db.workspace_id,
            workspace_name=db.workspace_name,
        )
        for db in user_workspace_dbs
        if db.workspace_id in calling_user_admin_workspace_ids
    ]
    if retrieved_workspaces:
        return retrieved_workspaces

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Calling user is not an admin in the same workspace as the user.",
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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    calling_user_workspace_role = await get_user_role_in_workspace(
        asession=asession, user_db=calling_user_db, workspace_db=workspace_db
    )

    if calling_user_workspace_role != UserRoles.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Calling user does not have the correct role to request a new API "
            "key for the workspace.",
        )

    new_api_key = generate_key()

    try:
        # This is necessary to attach the `workspace_db` object to the session.
        asession.add(workspace_db)
        await asession.flush()
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

    username = calling_user_db.username
    workspace_name = workspace_switch.workspace_name
    user_workspace_dbs = await get_user_workspaces(
        asession=asession, user_db=calling_user_db
    )
    user_workspace_db = next(
        (db for db in user_workspace_dbs if db.workspace_name == workspace_name), None
    )

    if user_workspace_db is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workspace with workspace name '{workspace_name}' not found.",
        )

    user_role = await get_user_role_in_workspace(
        asession=asession, user_db=calling_user_db, workspace_db=user_workspace_db
    )

    if user_role is None or user_role not in UserRoles:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid user role when switching to workspace.",
        )

    # Hardcode "fullaccess" now, but may use it in the future.
    return AuthenticationDetails(
        access_level="fullaccess",
        access_token=create_access_token(
            user_role=user_role, username=username, workspace_name=workspace_name
        ),
        token_type="bearer",
        user_role=user_role,
        username=username,
        workspace_name=workspace_name,
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

    workspace_db_checked = await check_update_workspace_call(
        asession=asession,
        calling_user_db=calling_user_db,
        workspace=workspace,
        workspace_id=workspace_id,
    )

    try:
        # This is necessary to attach the `workspace_db` object to the session.
        asession.add(workspace_db_checked)
        await asession.flush()
        workspace_db_updated = await update_workspace_name_and_quotas(
            asession=asession, workspace=workspace, workspace_db=workspace_db_checked
        )
        new_api_daily_quota = (
            workspace_db_checked.api_daily_quota
            if workspace_db_updated.api_daily_quota
            == workspace_db_checked.api_daily_quota
            else workspace_db_updated.api_daily_quota
        )
        new_content_quota = (
            workspace_db_checked.content_quota
            if workspace_db_updated.content_quota == workspace_db_checked.content_quota
            else workspace_db_updated.content_quota
        )
        new_workspace_name = (
            workspace_db_checked.workspace_name
            if workspace_db_updated.workspace_name
            == workspace_db_checked.workspace_name
            else workspace_db_updated.workspace_name
        )
        return WorkspaceUpdate(
            api_daily_quota=new_api_daily_quota,
            content_quota=new_content_quota,
            workspace_name=new_workspace_name,
        )
    except SQLAlchemyError as e:
        logger.error(f"Error updating workspace information: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating workspace information.",
        ) from e


async def check_update_workspace_call(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    workspace: WorkspaceUpdate,
    workspace_id: int,
) -> WorkspaceDB:
    """Check the workspace update call to ensure the action is allowed.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is updating the workspace.
    workspace
        The workspace object with the updated information.
    workspace_id
        The workspace ID to update.

    Returns
    -------
    WorkspaceDB
        The workspace object to update.

    Raises
    ------
    HTTPException
        If no valid updates are provided for the workspace.
        If the workspace to update does not exist.
        If the workspace name is not valid.
        If the calling user is not an admin in the workspace.
    """

    api_daily_quota = workspace.api_daily_quota
    content_quota = workspace.content_quota
    workspace_name = workspace.workspace_name

    updating_api_daily_quota = api_daily_quota is None or api_daily_quota >= 0
    updating_content_quota = content_quota is None or content_quota >= 0

    if not any(
        [
            updating_api_daily_quota,
            updating_content_quota,
            workspace_name is not None,
        ]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid updates provided for the workspace.",
        )

    try:
        workspace_db = await get_workspace_by_workspace_id(
            asession=asession, workspace_id=workspace_id
        )
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace ID {workspace_id} not found.",
        ) from e

    if workspace_name is not None and not await is_workspace_name_valid(
        asession=asession, workspace_name=workspace_name
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workspace with workspace name {workspace_name} already exists.",
        )

    calling_user_workspace_role = await get_user_role_in_workspace(
        asession=asession, user_db=calling_user_db, workspace_db=workspace_db
    )

    if calling_user_workspace_role != UserRoles.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Calling user is not an admin in the workspace.",
        )

    return workspace_db
