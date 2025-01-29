"""This module contains FastAPI routers for user creation and registration endpoints."""

from typing import Annotated, Optional

import sqlalchemy
from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_workspace_name
from ..database import get_async_session
from ..utils import setup_logger, update_api_limits
from ..workspaces.utils import (
    WorkspaceNotFoundError,
    check_if_workspaces_exist,
    create_workspace,
    get_workspace_by_workspace_name,
)
from .models import (
    UserDB,
    UserNotFoundError,
    UserNotFoundInWorkspaceError,
    UserWorkspaceRoleAlreadyExistsError,
    WorkspaceDB,
    check_if_user_exists,
    check_if_user_exists_in_workspace,
    check_if_users_exist,
    create_user_workspace_role,
    get_admin_users_in_workspace,
    get_user_by_id,
    get_user_by_username,
    get_user_role_in_all_workspaces,
    get_user_role_in_workspace,
    get_users_and_roles_by_workspace_id,
    get_workspaces_by_user_role,
    is_username_valid,
    remove_user_from_dbs,
    reset_user_password_in_db,
    save_user_to_db,
    update_user_default_workspace,
    update_user_in_db,
    update_user_role_in_workspace,
    user_has_admin_role_in_any_workspace,
    user_has_required_role_in_workspace,
    users_exist_in_workspace,
)
from .schemas import (
    RequireRegisterResponse,
    UserCreate,
    UserCreateWithCode,
    UserCreateWithPassword,
    UserRemove,
    UserRemoveResponse,
    UserResetPassword,
    UserRetrieve,
    UserRoles,
    UserUpdate,
)
from .utils import generate_recovery_codes

TAG_METADATA = {
    "name": "User",
    "description": "_Requires user login._ Manages users. Admin users have access to "
    "all endpoints. Other users have limited access.",
}

router = APIRouter(prefix="/user", tags=["User"])
logger = setup_logger()


@router.post("/", response_model=UserCreateWithCode)
async def create_user(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    user: UserCreateWithPassword,
    asession: AsyncSession = Depends(get_async_session),
) -> UserCreateWithCode:
    """Create a user. If the user does not exist, then a new user is created in the
    specified workspace with the specified role. Otherwise, the existing user is added
    to the specified workspace with the specified role. In all cases, the specified
    workspace must be created already.

    NB: This endpoint can also be used to create a new user in a different workspace
    than the calling user or be used to add an existing user to a workspace that the
    calling user is an admin of.

    NB: This endpoint does NOT update API limits for the workspace that the created
    user is being assigned to. This is because API limits are set at the workspace
    level when the workspace is first created and not at the user level.

    The process is as follows:

    1. Parameters for the endpoint are checked first.
    2. If the user does not exist, then create the user and add the user to the
        specified workspace with the specified role. In addition, the specified
        workspace is set as the default workspace.
    3. If the user exists, then add the user to the specified workspace with the
        specified role. In this case, there is the option to set the workspace as the
        default workspace for the user.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user that is creating a user.
    user
        The user object to create.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    UserCreateWithCode
        The user object with the recovery codes.

    Raises
    ------
    HTTPException
        If the user is already assigned a role in the specified workspace.
    """

    # 1.
    user_checked, user_checked_workspace_db = await check_create_user_call(
        asession=asession, calling_user_db=calling_user_db, user=user
    )
    assert user_checked.workspace_name

    try:
        # 3.
        return await add_existing_user_to_workspace(
            asession=asession, user=user_checked, workspace_db=user_checked_workspace_db
        )
    except UserNotFoundError:
        # 2.
        return await add_new_user_to_workspace(
            asession=asession, user=user_checked, workspace_db=user_checked_workspace_db
        )
    except UserWorkspaceRoleAlreadyExistsError as e:
        logger.error(f"Error creating user workspace role: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User workspace role already exists.",
        ) from e


@router.post("/register-first-user", response_model=UserCreateWithCode)
async def create_first_user(
    user: UserCreateWithPassword,
    request: Request,
    asession: AsyncSession = Depends(get_async_session),
    default_workspace_name: Optional[str] = None,
) -> UserCreateWithCode:
    """Create the first user. This occurs when there are no users in the `UserDB`
    database AND no workspaces in the `WorkspaceDB` database. The first user is created
    as an ADMIN user in the workspace `default_workspace_name`; if not provided, then
    the default workspace name is f`Workspace_{user.username}`. Thus, there is no need
    to specify the workspace name and user role for the very first user.

    Furthermore, the API daily quota and content quota is set to `None` for the default
    workspace. After the default workspace is created for the first user, the first
    user should then create a new workspace with a designated ADMIN user role and set
    the API daily quota and content quota for that workspace accordingly.

    The process is as follows:

    1. Create the very first workspace for the very first user. No quotas are set, the
        user role defaults to ADMIN and the workspace name defaults to
        `default_workspace_name`.
    2. Add the very first user to the default workspace with the ADMIN role and assign
        the workspace as the default workspace for the first user.
    3. Update the API limits for the workspace.

    Parameters
    ----------
    user
        The object to use for user creation.
    request
        The request object.
    asession
        The SQLAlchemy async session to use for all database connections.
    default_workspace_name
        The default workspace name for the very first user.

    Returns
    -------
    UserCreateWithCode
        The created user object with the recovery codes.

    Raises
    ------
    HTTPException
        If there are already users assigned to workspaces.
    """

    users_exist = await check_if_users_exist(asession=asession)
    workspaces_exist = await check_if_workspaces_exist(asession=asession)
    if users_exist and workspaces_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There are already users assigned to workspaces.",
        )

    # 1.
    user.role = UserRoles.ADMIN
    user.workspace_name = default_workspace_name or f"Workspace_{user.username}"
    workspace_db_new = await create_workspace(asession=asession, user=user)

    # 2.
    user_new = await add_new_user_to_workspace(
        asession=asession, user=user, workspace_db=workspace_db_new
    )

    # 3.
    await update_api_limits(
        api_daily_quota=workspace_db_new.api_daily_quota,
        redis=request.app.state.redis,
        workspace_name=workspace_db_new.workspace_name,
    )

    return user_new


@router.delete("/{user_id}", response_model=UserRemoveResponse)
async def remove_user_from_workspace(
    user: UserRemove,
    user_id: int,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> UserRemoveResponse:
    """Remove user by ID from workspace. Users can only be removed from a workspace by
    admin users of that workspace.

    Note:

    1. There should be no scenarios where the **last** admin user of a workspace is
        allowed to remove themselves from the workspace. This poses a data risk since
        an existing workspace with no users means that ANY admin can add users to that
        workspace---this is essentially the scenario when an admin creates a new
        workspace and then proceeds to add users to that newly created workspace.
        However, existing workspaces can have content; thus, we disable the ability to
        remove the last admin user from a workspace.
    2. All workspaces must have at least one ADMIN user.
    3. A re-authentication should be triggered by the frontend if the calling user is
        removing themselves from the only workspace that they are assigned to. This
        scenario can still occur if there are two admins of a workspace and an admin
        is only assigned to that workspace and decides to remove themselves from the
        workspace.
    4. A workspace login should be triggered by the frontend if the calling user is
        removing themselves from the current workspace. This occurs when
        `require_workspace_login` is set to `True` in `UserRemoveResponse`. Case 3
        supersedes this case.

    The process is as follows:

    1. If the user is assigned to the specified workspace, then the user (and their
        role) is removed from that workspace. If the specified workspace was the user's
        default workspace, then the next workspace that the user is assigned to is set
        as the user's default workspace.
    2. If the user is not assigned to any workspace after being removed from the
        specified workspace, then the user is also deleted from the `UserDB` database.
        This is necessary because a user must be assigned to at least one workspace.

    Parameters
    ----------
    user
        The user object with the name of the workspace to remove the user from.
    user_id
        The user ID to remove from the specified workspace.
    calling_user_db
        The user object associated with the user that is removing the user from the
        specified workspace.
    workspace_name
        The name of the workspace that the calling user is currently logged into. This
        is used to detect if the calling user is removing themselves from the current
        workspace. If so, then a workspace login will be triggered.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    UserRemoveResponse
        The response object with the user's default workspace name after removal and
        the workspace from which they were removed.

    Raises
    ------
    HTTPException
        IF the user is not found in the workspace to be removed from.
        If the removal of the user from the specified workspace is not allowed.
    """

    remove_from_workspace_db, user_db = await check_remove_user_from_workspace_call(
        asession=asession, calling_user_db=calling_user_db, user=user, user_id=user_id
    )

    # 1 and 2.
    try:
        (default_workspace_name, removed_from_workspace_name) = (
            await remove_user_from_dbs(
                asession=asession,
                remove_from_workspace_db=remove_from_workspace_db,
                user_db=user_db,
            )
        )
    except UserNotFoundInWorkspaceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in workspace.",
        ) from e
    except sqlalchemy.exc.IntegrityError as e:
        logger.error(f"Error deleting content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Deletion of content with feedback is not allowed.",
        ) from e

    self_removal = calling_user_db.user_id == user_id
    require_authentication = self_removal and default_workspace_name is None
    require_workspace_login = require_authentication or (
        self_removal and removed_from_workspace_name == workspace_name
    )
    return UserRemoveResponse(
        default_workspace_name=default_workspace_name,
        removed_from_workspace_name=removed_from_workspace_name,
        require_authentication=require_authentication,
        require_workspace_login=require_workspace_login,
    )


@router.get("/", response_model=list[UserRetrieve])
async def retrieve_all_users(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[UserRetrieve]:
    """Return a list of all users.

    NB: When this endpoint called, it **should** be called by ADMIN users only since
    details about users and workspaces are returned. However, any given user should
    also be able to retrieve information about themselves even if they are not ADMIN
    users.

    The process is as follows:

    1. Only retrieve workspaces for which the calling user has an ADMIN role.
    2. If the calling user is an admin in a workspace, then the details for that
        workspace are returned.
    3. If the calling user is not an admin in any workspace, then the details for
        the calling user is returned.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user that is retrieving the list of users.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[UserRetrieve]
        A list of retrieved user objects.
    """

    user_mapping: dict[str, UserRetrieve] = {}

    # 1.
    calling_user_admin_workspace_dbs = await get_workspaces_by_user_role(
        asession=asession, user_db=calling_user_db, user_role=UserRoles.ADMIN
    )

    # 2.
    for workspace_db in calling_user_admin_workspace_dbs:
        workspace_id = workspace_db.workspace_id
        workspace_name = workspace_db.workspace_name
        user_workspace_roles = await get_users_and_roles_by_workspace_id(
            asession=asession, workspace_id=workspace_id
        )
        for uwr in user_workspace_roles:
            if uwr.username not in user_mapping:
                user_mapping[uwr.username] = UserRetrieve(
                    created_datetime_utc=uwr.created_datetime_utc,
                    is_default_workspace=[uwr.default_workspace],
                    updated_datetime_utc=uwr.updated_datetime_utc,
                    username=uwr.username,
                    user_id=uwr.user_id,
                    user_workspace_names=[workspace_name],
                    user_workspace_roles=[uwr.user_role.value],
                )
            else:
                user_data = user_mapping[uwr.username]
                user_data.is_default_workspace.append(uwr.default_workspace)
                user_data.user_workspace_names.append(workspace_name)
                user_data.user_workspace_roles.append(uwr.user_role.value)

    user_list = list(user_mapping.values())

    # 3.
    if not user_list:
        calling_user_workspace_roles = await get_user_role_in_all_workspaces(
            asession=asession, user_db=calling_user_db
        )
        user_list = [
            UserRetrieve(
                created_datetime_utc=calling_user_db.created_datetime_utc,
                is_default_workspace=[
                    row.default_workspace for row in calling_user_workspace_roles
                ],
                updated_datetime_utc=calling_user_db.updated_datetime_utc,
                username=calling_user_db.username,
                user_id=calling_user_db.user_id,
                user_workspace_names=[
                    row.workspace_name for row in calling_user_workspace_roles
                ],
                user_workspace_roles=[
                    row.user_role.value for row in calling_user_workspace_roles
                ],
            )
        ]

    return user_list


@router.get("/require-register", response_model=RequireRegisterResponse)
async def is_register_required(
    asession: AsyncSession = Depends(get_async_session),
) -> RequireRegisterResponse:
    """Initial registration is required if there are neither users nor workspaces in
    the `UserDB` and `WorkspaceDB` databases.

    NB: If there is a user in the `UserDB` database, then there must be at least one
    workspace (i.e., the workspace that the user should have been assigned to when the
    user was first created). If there are no users, then there cannot be any workspaces
    either.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    RequireRegisterResponse
        The response object containing the boolean value for whether user registration
    is required.
    """

    users_exist = await check_if_users_exist(asession=asession)
    workspaces_exist = await check_if_workspaces_exist(asession=asession)
    assert (users_exist and workspaces_exist) or not (users_exist and workspaces_exist)
    return RequireRegisterResponse(
        require_register=not (users_exist and workspaces_exist)
    )


@router.put("/reset-password", response_model=UserRetrieve)
async def reset_password(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    user: UserResetPassword,
    asession: AsyncSession = Depends(get_async_session),
) -> UserRetrieve:
    """Reset user password. Takes a user object, generates a new password, replaces the
    old one in the database, and returns the updated user object.

    NB: When this endpoint is called, the assumption is that the calling user is the
    user that is requesting to reset their own password. In other words, an admin of a
    given workspace **cannot** reset the password of a user in their workspace. This is
    because a user can belong to multiple workspaces with different admins. However, a
    user's password is universal and belongs to the user and not a workspace. Thus,
    only a user can reset their own password.

    NB: Since the `retrieve_all_users` endpoint is invoked first to display the correct
    users for the calling user's workspaces, there should be no scenarios where a user
    is resetting the password of another user.

    The process is as follows:

    1. The user password is reset in the `UserDB` database.
    2. The user's role in all workspaces is retrieved for the return object.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user resetting the password.
    user
        The user object with the new password and recovery code.
    asession
        The async session to use for the database connection.

    Returns
    -------
    UserRetrieve
        The updated user object.
    """

    user_to_update = await check_reset_password_call(
        asession=asession, calling_user_db=calling_user_db, user=user
    )

    # 1.
    updated_recovery_codes = [
        val for val in user_to_update.recovery_codes if val != user.recovery_code
    ]
    updated_user_db = await reset_user_password_in_db(
        asession=asession,
        user=user,
        user_id=user_to_update.user_id,
        recovery_codes=updated_recovery_codes,
    )

    # 2.
    updated_user_workspace_roles = await get_user_role_in_all_workspaces(
        asession=asession, user_db=updated_user_db
    )

    return UserRetrieve(
        created_datetime_utc=updated_user_db.created_datetime_utc,
        is_default_workspace=[
            row.default_workspace for row in updated_user_workspace_roles
        ],
        updated_datetime_utc=updated_user_db.updated_datetime_utc,
        username=updated_user_db.username,
        user_id=updated_user_db.user_id,
        user_workspace_names=[
            row.workspace_name for row in updated_user_workspace_roles
        ],
        user_workspace_roles=[row.user_role for row in updated_user_workspace_roles],
    )


@router.put("/{user_id}", response_model=UserRetrieve)
async def update_user(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    user_id: int,
    user: UserUpdate,
    asession: AsyncSession = Depends(get_async_session),
) -> UserRetrieve:
    """Update the user's name, role in a workspace, and/or their default workspace. If
    a user belongs to multiple workspaces, then an admin in any of those workspaces is
    allowed to update the user's name and/or default workspace only. However, only
    admins of a workspace can modify their user's role in that workspace.

    NB: User information can only be updated by admin users. Furthermore, admin users
    can only update the information of users belonging to their workspaces. Since the
    `retrieve_all_users` endpoint is invoked first to display the correct users for the
    calling user's workspaces, there should be no issue with an admin user updating
    user information for users in other workspaces. This endpoint will also check that
    the calling user is an admin in any workspace.

    NB: A user's API daily quota limit and content quota can no longer be updated since
    these are set at the workspace level when the workspace is first created. Instead,
    the `update_workspace` endpoint should be called to make changes to (existing)
    workspaces.

    The process is as follows:

    1. Parameters for the endpoint are checked first.
    2. If the user's workspace role is being updated, then the update procedure will
        update the user's role in that workspace. This step will error out if the user
        being updated is not part of the specified workspace.
    3. Update the user's default workspace. This step will error out if the user
        being updated is not part of the specified workspace.
    4. Update the user's name in the database.
    5. Retrieve the updated user's role in all workspaces for the return object.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user updating the user.
    user_id
        The user ID to update.
    user
        The user object with the updated information.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    UserRetrieve
        The updated user object.

    Raises
    ------
    HTTPException
        If the user is not found in the workspace.
    """

    # 1.
    user_db_checked, workspace_db_checked = await check_update_user_call(
        asession=asession, calling_user_db=calling_user_db, user=user, user_id=user_id
    )

    # 2.
    if user.role and user.workspace_name and workspace_db_checked:
        try:
            await update_user_role_in_workspace(
                asession=asession,
                new_role=user.role,
                user_db=user_db_checked,
                workspace_db=workspace_db_checked,
            )
        except UserNotFoundInWorkspaceError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User ID '{user_id}' not found in workspace.",
            ) from e

    # 3.
    if user.is_default_workspace and user.workspace_name and workspace_db_checked:
        try:
            await update_user_default_workspace(
                asession=asession,
                user_db=user_db_checked,
                workspace_db=workspace_db_checked,
            )
        except UserNotFoundInWorkspaceError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User ID '{user_id}' not found in workspace.",
            ) from e

    # 4.
    updated_user_db = await update_user_in_db(
        asession=asession, user=user, user_id=user_id
    )

    # 5.
    updated_user_workspace_roles = await get_user_role_in_all_workspaces(
        asession=asession, user_db=updated_user_db
    )

    return UserRetrieve(
        created_datetime_utc=updated_user_db.created_datetime_utc,
        is_default_workspace=[
            row.default_workspace for row in updated_user_workspace_roles
        ],
        updated_datetime_utc=updated_user_db.updated_datetime_utc,
        username=updated_user_db.username,
        user_id=updated_user_db.user_id,
        user_workspace_names=[
            row.workspace_name for row in updated_user_workspace_roles
        ],
        user_workspace_roles=[
            row.user_role.value for row in updated_user_workspace_roles
        ],
    )


@router.get("/current-user", response_model=UserRetrieve)
async def get_user(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> UserRetrieve:
    """Retrieve the user object for the calling user.

    NB: The assumption here is that any user can retrieve their own user object.

    Parameters
    ----------
    user_db
        The user object associated with the user that is being retrieved.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    UserRetrieve
        The retrieved user object.

    Raises
    ------
    HTTPException
        If the calling user does not have the correct access to retrieve the user.
    """

    user_workspace_roles = await get_user_role_in_all_workspaces(
        asession=asession, user_db=user_db
    )
    return UserRetrieve(
        created_datetime_utc=user_db.created_datetime_utc,
        is_default_workspace=[row.default_workspace for row in user_workspace_roles],
        updated_datetime_utc=user_db.updated_datetime_utc,
        user_id=user_db.user_id,
        username=user_db.username,
        user_workspace_names=[row.workspace_name for row in user_workspace_roles],
        user_workspace_roles=[row.user_role.value for row in user_workspace_roles],
    )


async def add_existing_user_to_workspace(
    *,
    asession: AsyncSession,
    user: UserCreate | UserCreateWithPassword,
    workspace_db: WorkspaceDB,
) -> UserCreateWithCode:
    """The process for adding an existing user to a workspace is:

    1. Retrieve the existing user from the `UserDB` database.
    2. Add the existing user to the workspace with the specified role.

    NB: If this function is invoked, then the assumption is that it is called by an
    ADMIN user with access to the specified workspace and that this ADMIN user is
    adding an **existing** user to the workspace with the specified user role.

    NB: We do not update the API limits for the workspace when an existing user is
    added to the workspace. This is because the API limits are set at the workspace
    level when the workspace is first created by the admin and not at the user level.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user
        The user object to use for adding the existing user to the workspace.
    workspace_db
        The workspace object to use.

    Returns
    -------
    UserCreateWithCode
        The user object with the recovery codes.
    """

    assert user.role is not None
    user.is_default_workspace = user.is_default_workspace or False

    # 1.
    user_db = await get_user_by_username(asession=asession, username=user.username)

    # 2.
    _ = await create_user_workspace_role(
        asession=asession,
        is_default_workspace=user.is_default_workspace,
        user_db=user_db,
        user_role=user.role,
        workspace_db=workspace_db,
    )

    return UserCreateWithCode(
        recovery_codes=user_db.recovery_codes,
        role=user.role,
        username=user_db.username,
        workspace_name=workspace_db.workspace_name,
    )


async def add_new_user_to_workspace(
    *,
    asession: AsyncSession,
    user: UserCreate | UserCreateWithPassword,
    workspace_db: WorkspaceDB,
) -> UserCreateWithCode:
    """The process for adding a new user to a workspace is:

    1. Generate recovery codes for the new user.
    2. Save the new user to the `UserDB` database along with their recovery codes.
    3. Add the new user to the workspace with the specified role. For new users, this
        workspace is set as their default workspace.

    NB: If this function is invoked, then the assumption is that it is called by an
    ADMIN user with access to the specified workspace and that this ADMIN user is
    adding a **new** user to the workspace with the specified user role.

    NB: We do not update the API limits for the workspace when a new user is added to
    the workspace. This is because the API limits are set at the workspace level when
    the workspace is first created by the workspace admin and not at the user level.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user
        The user object to use for adding the new user to the workspace.
    workspace_db
        The workspace object to use.

    Returns
    -------
    UserCreateWithCode
        The user object with the recovery codes.
    """

    assert user.role is not None

    # 1.
    recovery_codes = generate_recovery_codes()

    # 2.
    user_db = await save_user_to_db(
        asession=asession, recovery_codes=recovery_codes, user=user
    )

    # 3.
    _ = await create_user_workspace_role(
        asession=asession,
        is_default_workspace=True,  # Should always be True for new users!
        user_db=user_db,
        user_role=user.role,
        workspace_db=workspace_db,
    )

    return UserCreateWithCode(
        recovery_codes=recovery_codes,
        role=user.role,
        username=user_db.username,
        workspace_name=workspace_db.workspace_name,
    )


async def check_remove_user_from_workspace_call(
    *, asession: AsyncSession, calling_user_db: UserDB, user: UserRemove, user_id: int
) -> tuple[WorkspaceDB, UserDB]:
    """Check the remove user from workspace call to ensure the action is allowed.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is removing the user from the
        specified workspace.
    user
        The user object with the name of the workspace to remove the user from.
    user_id
        The user ID to remove from the specified workspace.

    Returns
    -------
    tuple[WorkspaceDB, UserDB]
        The workspace and user objects to remove the user from.

    Raises
    ------
    HTTPException
        If the user does not have the required role to remove users from the specified
        workspace.
        If the user ID is not found.
        If the user is attempting to remove the last admin user from the specified
        workspace.
    """

    remove_from_workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=user.remove_workspace_name
    )

    # HACK FIX FOR FRONTEND: The frontend should hide/disable the ability to remove
    # users for non-admin users of a workspace.
    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=remove_from_workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to remove users from the "
            "specified workspace.",
        )
    # HACK FIX FOR FRONTEND: The frontend should hide/disable the ability to remove
    # users for non-admin users of a workspace.

    user_db = await get_user_by_id(asession=asession, user_id=user_id)

    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User ID `{user_id}` not found.",
        )

    workspace_admin_dbs = await get_admin_users_in_workspace(
        asession=asession, workspace_id=remove_from_workspace_db.workspace_id
    )
    assert workspace_admin_dbs is not None
    if len(workspace_admin_dbs) == 1 and workspace_admin_dbs[0].user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot remove last admin user from the workspace.",
        )

    return remove_from_workspace_db, user_db


async def check_create_user_call(
    *, asession: AsyncSession, calling_user_db: UserDB, user: UserCreateWithPassword
) -> tuple[UserCreateWithPassword, WorkspaceDB]:
    """Check the user creation call to ensure the action is allowed.

    NB: This function:

    1. Changes `user.workspace_name` to the workspace name of the calling user if it is
        not specified.
    2. Assigns a default role of READ ONLY if the role is not specified.

    The process is as follows:

    1. If a workspace is specified for the user being created and the workspace is not
        yet created, then an error is thrown. This is a safety net for the backend
        since the frontend should ensure that a user can only be created in existing
        workspaces.
    2. If the calling user is not an admin in any workspace, then an error is thrown.
        This is a safety net for the backend since the frontend should ensure that the
        ability to create a user is only available to admin users.
    3. If the workspace is not specified for the user and the calling user belongs to
        multiple workspaces, then an error is thrown. This is a safety net for the
        backend since the frontend should ensure that a workspace is specified when
        creating a user.
    4. If the calling user is not an admin in the workspace specified for the user and
        the specified workspace exists with users and roles, then an error is thrown.
        In this case, the calling user must be an admin in the specified workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is creating a user.
    user
        The user object to create.

    Returns
    -------
    tuple[UserCreateWithPassword, WorkspaceDB]
        The user and workspace objects to create.

    Raises
    ------
    HTTPException
        If a workspace is specified for the user being created and the workspace is not
        yet created.
        If the calling user does not have the correct role to create a user in any
        workspace.
        If the user workspace is not specified and the calling user belongs to multiple
        workspaces.
        If the user workspace is specified and the calling user does not have the
        correct role in the specified workspace.
    """

    # 1.
    if user.workspace_name:
        try:
            _ = await get_workspace_by_workspace_name(
                asession=asession, workspace_name=user.workspace_name
            )
        except WorkspaceNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workspace does not exist: {user.workspace_name}",
            ) from e

    # 2.
    if not await user_has_admin_role_in_any_workspace(
        asession=asession, user_db=calling_user_db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Calling user does not have the correct role to create a user in "
            "any workspace.",
        )

    calling_user_admin_workspace_dbs = await get_workspaces_by_user_role(
        asession=asession, user_db=calling_user_db, user_role=UserRoles.ADMIN
    )

    # 3.
    if not user.workspace_name and len(calling_user_admin_workspace_dbs) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calling user belongs to multiple workspaces. A workspace must be "
            "specified for creating a user.",
        )

    # 4.
    if user.workspace_name:
        calling_user_in_specified_workspace = next(
            (
                workspace_db
                for workspace_db in calling_user_admin_workspace_dbs
                if workspace_db.workspace_name == user.workspace_name
            ),
            None,
        )
        workspace_has_users = await users_exist_in_workspace(
            asession=asession, workspace_name=user.workspace_name
        )

        if not calling_user_in_specified_workspace and workspace_has_users:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Calling user does not have the correct role in the specified "
                f"workspace: {user.workspace_name}",
            )
    else:
        # NB: `user.workspace_name` is updated here!
        user.workspace_name = calling_user_admin_workspace_dbs[0].workspace_name

    # NB: `user.role` is updated here!
    user.role = user.role or UserRoles.READ_ONLY

    assert user.workspace_name is not None
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=user.workspace_name
    )

    return user, workspace_db


async def check_reset_password_call(
    *, asession: AsyncSession, calling_user_db: UserDB, user: UserResetPassword
) -> UserDB:
    """Check the reset password call to ensure the action is allowed.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is resetting the password.
    user
        The user object with the new password and recovery code.

    Returns
    -------
    UserDB
        The user object to update.

    Raises
    ------
    HTTPException
        If the calling user is not the user resetting the password.
        If the user to update is not found.
        If the recovery code is incorrect.
    """

    if calling_user_db.username != user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Calling user is not the user resetting the password.",
        )

    user_to_update = await check_if_user_exists(asession=asession, user=user)

    if user_to_update is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    if user.recovery_code not in user_to_update.recovery_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recovery code is incorrect.",
        )

    return user_to_update


async def check_update_user_call(
    *, asession: AsyncSession, calling_user_db: UserDB, user_id: int, user: UserCreate
) -> tuple[UserDB, WorkspaceDB | None]:
    """Check the user update call to ensure the action is allowed.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is updating the user.
    user_id
        The user ID to update.
    user
        The user object with the updated information.

    Returns
    -------
    tuple[UserDB, WorkspaceDB]
        The user and workspace objects to update.

    Raises
    ------
    HTTPException
        If the calling user does not have the correct access to update the user.
        If a user's role is being changed but the workspace name is not specified.
        If a user's default workspace is being changed but the workspace name is not
            specified.
        If the user to update is not found.
        If the username is already taken.
        If the calling user is not an admin in the workspace.
        If the user does not belong to the specified workspace.
    """

    if not await user_has_admin_role_in_any_workspace(
        asession=asession, user_db=calling_user_db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Calling user does not have the correct role to update user "
            "information.",
        )

    if user.role and not user.workspace_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace name must be specified if user's role is being updated.",
        )

    if user.is_default_workspace is not None and not user.workspace_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace name must be specified if user's default workspace is "
            "being updated.",
        )

    try:
        user_db = await get_user_by_id(asession=asession, user_id=user_id)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User ID {user_id} not found.",
        ) from e

    if user.username != user_db.username and not await is_username_valid(
        asession=asession, username=user.username
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with username {user.username} already exists.",
        )

    workspace_db = None
    if user.role and user.workspace_name:
        workspace_db = await get_workspace_by_workspace_name(
            asession=asession, workspace_name=user.workspace_name
        )
        calling_user_workspace_role = await get_user_role_in_workspace(
            asession=asession, user_db=calling_user_db, workspace_db=workspace_db
        )

        if calling_user_workspace_role != UserRoles.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Calling user is not an admin in the workspace.",
            )

        if not await check_if_user_exists_in_workspace(
            asession=asession,
            user_id=user_db.user_id,
            workspace_id=workspace_db.workspace_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User ID '{user_db.user_id}' does belong to workspace ID "
                f"'{workspace_db.workspace_id}'.",
            )

    return user_db, workspace_db
