"""This module contains FastAPI routers for user creation and registration endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user, get_current_workspace_name
from app.core.config import RATE_LIMIT_AUTH
from app.core.database import get_async_session
from app.core.security import get_client_ip, limiter
from app.users.models import UserDB
from app.users.schemas import (
    RequireRegisterResponse,
    UserCreate,
    UserCreateWithCode,
    UserCreateWithPassword,
    UserRemoveResponse,
    UserResetPassword,
    UserRetrieve,
    UserUpdate,
)
from app.users.service import (
    add_user_to_workspace,
    check_register_required,
    check_username_exists,
    create_user_in_workspace,
    delete_user_from_workspace,
    get_user_details,
    list_users_in_workspace,
    register_first_user,
    reset_user_password,
    update_user_details,
)

TAG_METADATA = {
    "name": "User",
    "description": "_Requires user login._ Manages users. Admin users have access to "
    "all endpoints. Other users have limited access.",
}

router = APIRouter(prefix="/user", tags=["User"])


@router.post("/", response_model=UserCreateWithCode)
async def create_new_user(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    user: UserCreateWithPassword,
    asession: AsyncSession = Depends(get_async_session),
) -> UserCreateWithCode:
    """Create a new user in an **existing** workspace. New user creation requires a
    user password.

    NB: This endpoint does NOT update API limits for the workspace that the created
    user is being assigned to. This is because API limits are set at the workspace
    level when the workspace is first created and not at the user level.

    The process is as follows:

    1. If the username already exists, then raise a 400 error. In this case, the
        frontend should add the existing user to a workspace instead (i.e., invoke the
        `/user/existing-user` endpoint).
    2. The rest of the parameters for creating a new user in a workspace are checked.
    3. Create the new user and add the user to the specified workspace with the
        specified role. In addition, the specified workspace is set as the new user's
        default workspace.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user that is creating a new user.
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
        If the username already exists.
    """

    return await create_user_in_workspace(
        asession=asession, calling_user_db=calling_user_db, user=user
    )


@router.post("/add-existing-user-to-workspace", response_model=UserCreateWithCode)
async def add_existing_user(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    user: UserCreate,
    asession: AsyncSession = Depends(get_async_session),
) -> UserCreateWithCode:
    """Add an existing user to an **existing** workspace. This does not require a user
    password.

    NB: This endpoint does NOT update API limits for the workspace that the created
    user is being assigned to. This is because API limits are set at the workspace
    level when the workspace is first created and not at the user level.

    The process is as follows:

    1. If the user does not exist, then raise a 404 error. In this case, the frontend
        should create a new user instead (i.e., invoke the `/user/` endpoint).
    2. The rest of the parameters for adding an existing user to a workspace are
        checked.
    3. Add the existing user to the specified workspace with the specified role. In
        this case, there is the option to also set the workspace as the default
        workspace for the user.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user that is adding an existing user.
    user
        The user object to add.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    UserCreateWithCode
        The user object with the recovery codes.

    Raises
    ------
    HTTPException
        If the username does not exist.
        If the user is already assigned a role in the specified workspace.
    """

    return await add_user_to_workspace(
        asession=asession, calling_user_db=calling_user_db, user=user
    )


@router.post("/register-first-user", response_model=UserCreateWithCode)
@limiter.limit(RATE_LIMIT_AUTH, key_func=get_client_ip)
async def create_first_user(
    user: UserCreateWithPassword,
    request: Request,
    asession: AsyncSession = Depends(get_async_session),
) -> UserCreateWithCode:
    """Create the first user. This occurs when there are no users in the `UserDB`
    database AND no workspaces in the `WorkspaceDB` database. The first user is created
    as an ADMIN user in the workspace specified by `user`; if not provided, then the
    default workspace name is f`Workspace_{user.username}`. Thus, there is no need to
    specify the workspace name and user role for the very first user.

    Furthermore, the API daily quota and content quota is set to `None` for the default
    workspace and the document language defaults to the one set by the global config
    (or English if not set). After the default workspace is created for the first user,
    the first user should then create a new workspace with a designated ADMIN user role
    and set workspace attributes accordingly.

    The process is as follows:

    1. Create the very first workspace for the very first user. No quotas are set, the
        default document language is set, and the user role defaults to ADMIN.
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

    Returns
    -------
    UserCreateWithCode
        The created user object with the recovery codes.

    Raises
    ------
    HTTPException
        If there are already users assigned to workspaces.
    """

    return await register_first_user(
        asession=asession, redis=request.app.state.redis, user=user
    )


@router.delete("/{user_id}", response_model=UserRemoveResponse)
async def remove_user_from_workspace(
    user_id: int,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    remove_from_workspace_name: str = Query(
        ..., description="Name of the workspace to remove the user from."
    ),
    asession: AsyncSession = Depends(get_async_session),
) -> UserRemoveResponse:
    """Remove user by ID from workspace. Users can only be removed from a workspace by
    admin users of that workspace.

    Note:

    1. There should be no scenarios where the **last** admin user of a workspace is
        allowed to remove themselves from the workspace. This poses a data risk since
        an existing workspace with no users means that ANY admin can add users to that
        workspace---this is the same scenario as when an admin creates a new workspace
        and then proceeds to add users to that newly created workspace. However,
        existing workspaces can have content; thus, we disable the ability to remove
        the last admin user from a workspace.
    2. All workspaces must have at least one ADMIN user.
    3. A re-authentication should be triggered by the frontend if the calling user is
        removing themselves from the only workspace that they are assigned to. This
        scenario can still occur if there are two admins of a workspace and an admin
        is only assigned to that workspace and decides to remove themselves from the
        workspace.
    4. A workspace switch should be triggered by the frontend if the calling user is
        removing themselves from the current workspace. This occurs when
        `require_workspace_switch` is set to `True` in `UserRemoveResponse`. Case 3
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
    user_id
        The user ID to remove from the specified workspace.
    calling_user_db
        The user object associated with the user that is removing the user from the
        specified workspace.
    workspace_name
        The name of the workspace that the calling user is currently logged into. This
        is used to detect if the calling user is removing themselves from the current
        workspace. If so, then a workspace login will be triggered.
    remove_from_workspace_name
        The name of the workspace from which the user is being removed.
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

    return await delete_user_from_workspace(
        asession=asession,
        calling_user_db=calling_user_db,
        remove_from_workspace_name=remove_from_workspace_name,
        user_id=user_id,
        workspace_name=workspace_name,
    )


@router.get("/", response_model=list[UserRetrieve])
async def retrieve_all_users_in_current_workspace(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[UserRetrieve]:
    """Return a list of all users in the current workspace.

    NB: When this endpoint called, it **should** be called by ADMIN users only since
    details about users and their current workspace are returned. However, any given
    user should also be able to retrieve information about themselves even if they are
    not ADMIN users.

    The process is as follows:

    1. If the calling user is an admin in the current workspace, then the details of
        all users in the current workspace are returned.
    2. Otherwise, only the details of the calling user is returned.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user that is retrieving the list of users.
    workspace_name
        The name of the workspace that the calling user is currently logged into.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[UserRetrieve]
        A list of retrieved user objects.

    Raises
    ------
    HTTPException
        If the calling user does not have the required role to retrieve users in the
        current workspace.
    """

    return await list_users_in_workspace(
        asession=asession,
        calling_user_db=calling_user_db,
        workspace_name=workspace_name,
    )


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

    return await check_register_required(asession=asession)


# Public and guarded only by a recovery code, so limited per client IP.
@router.put("/reset-password", response_model=UserRetrieve)
@limiter.limit(RATE_LIMIT_AUTH, key_func=get_client_ip)
async def reset_password(
    request: Request,
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

    NB: Since the `retrieve_all_users_in_current_workspace` endpoint should be invoked
    first to display the correct users for the calling user's workspaces, there should
    be no scenarios where a user is resetting the password of another user.

    The process is as follows:

    1. The user password is reset in the `UserDB` database.
    2. The user's role in all workspaces is retrieved for the return object.

    Parameters
    ----------
    request
        The request object.
    user
        The user object with the new password and recovery code.
    asession
        The async session to use for the database connection.

    Returns
    -------
    UserRetrieve
        The updated user object.
    """

    return await reset_user_password(
        asession=asession, redis=request.app.state.redis, user=user
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
    `retrieve_all_users_in_current_workspace` endpoint should be invoked first to
    display the correct users for the calling user's workspaces, there should be no
    issue with an admin user updating user information for users in other workspaces.
    This endpoint will also check that the calling user is an admin in any workspace.

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

    return await update_user_details(
        asession=asession, calling_user_db=calling_user_db, user=user, user_id=user_id
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

    return await get_user_details(asession=asession, user_db=user_db)


@router.head("/{username}")
async def check_if_username_exists(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    username: str,
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """Check if a username exists in the database.

    NB: This endpoint should only be available to admin users. Although the check will
    pull global user records, the endpoint does not return details regarding user
    information, only a boolean.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user that is checking the username.
    username
        The username to check.
    asession
        The SQLAlchemy async session to use for all database connections.

    Raises
    ------
    HTTPException
        If the calling user does not have the correct role to check if a username
        exists.
        If the username does not exist.
    """

    await check_username_exists(
        asession=asession, calling_user_db=calling_user_db, username=username
    )
    return
