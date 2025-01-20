"""This module contains the FastAPI router for user creation and registration
endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_async_session
from ..users.models import (
    UserAlreadyExistsError,
    UserDB,
    UserNotFoundError,
    UserWorkspaceRoleAlreadyExistsError,
    WorkspaceDB,
    add_user_workspace_role,
    check_if_users_exist,
    check_if_workspaces_exist,
    create_workspace,
    get_user_by_id,
    get_user_by_username,
    get_user_role_in_all_workspaces,
    get_user_role_in_workspace,
    get_users_and_roles_by_workspace_name,
    get_workspace_by_workspace_name,
    is_username_valid,
    reset_user_password_in_db,
    save_user_to_db,
    update_user_in_db,
    update_user_role_in_workspace,
    update_workspace_api_key,
)
from ..users.schemas import (
    UserCreate,
    UserCreateWithCode,
    UserCreateWithPassword,
    UserResetPassword,
    UserRetrieve,
    UserRoles,
)
from ..utils import generate_key, setup_logger, update_api_limits
from .schemas import KeyResponse, RequireRegisterResponse
from .utils import generate_recovery_codes

TAG_METADATA = {
    "name": "Admin",
    "description": "_Requires user login._ Only administrator user has access to these "
    "endpoints.",
}

router = APIRouter(prefix="/user", tags=["Admin"])
logger = setup_logger()


@router.post("/", response_model=UserCreateWithCode)
async def create_user(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    user: UserCreateWithPassword,
    asession: AsyncSession = Depends(get_async_session),
) -> UserCreateWithCode:
    """Create a new user.

    NB: If the calling user only belongs to 1 workspace, then the created user is
    automatically assigned to that workspace. If a role is not specified for the new
    user, then the READ ONLY role is assigned to the new user.

    NB: DO NOT update the API limits for the workspace. This is because the API limits
    are set at the workspace level when the workspace is first created by the admin and
    not at the user level.

    The process is as follows:

    1. If a workspace is specified for the new user, then check that the calling user
        has ADMIN privileges in that workspace. If a workspace is not specified for the
        new user, then check that the calling user belongs to only 1 workspace (and is
        an ADMIN in that workspace).
    2. Add the new user to the appropriate workspace. If the role for the new user is
        not specified, then the READ ONLY role is assigned to the new user.

    Parameters
    ----------
    calling_user_db
        The user object associated with the user that is creating the new user.
    user
        The user object to create.
    asession
        The async session to use for the database connection.

    Returns
    -------
    UserCreateWithCode
        The user object with the recovery codes.

    Raises
    ------
    HTTPException
        If the calling user does not have the correct access to create a new user.
        If the user workspace is specified and the calling user does not have the
        correct access to the specified workspace.
        If the user workspace is not specified and the calling user belongs to multiple
        workspaces.
        If the user already exists or if the user workspace role already exists.
    """

    calling_user_workspace_roles = await get_user_role_in_all_workspaces(
        asession=asession, user_db=calling_user_db
    )
    if not any(
        row.user_role == UserRoles.ADMIN for row in calling_user_workspace_roles
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calling user does not have the correct access to create a new user "
                   "in any workspace.",
        )

    # 1.
    if user.workspace_name and next(
        (
            row.workspace_name
            for row in calling_user_workspace_roles
            if (
                row.workspace_name == user.workspace_name
                and row.user_role == UserRoles.ADMIN
            )
        ),
        None
    ) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Calling user does not have the correct access to the specified "
                   f"workspace: {user.workspace_name}",
        )
    elif len(calling_user_workspace_roles) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calling user belongs to multiple workspaces. A workspace must be "
                   "specified for creating the new user.",
        )
    else:
        user.workspace_name = calling_user_workspace_roles[0].workspace_name

    # 2.
    try:
        calling_user_workspace_db = await get_workspace_by_workspace_name(
            asession=asession, workspace_name=user.workspace_name
        )
        user.role = user.role or UserRoles.READ_ONLY
        user_new = await add_user_to_workspace(
            asession=asession, user=user, workspace_db=calling_user_workspace_db
        )
        return user_new
    except UserAlreadyExistsError as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with that username already exists.",
        ) from e
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
    default_workspace_name: str = "Workspace_SUPER_ADMINS",
) -> UserCreateWithCode:
    """Create the first user. This occurs when there are no users in the `UserDB`
    database AND no workspaces in the `WorkspaceDB` database. The first user is created
    as an ADMIN user in the default workspace `default_workspace_name`. Thus, there is
    no need to specify the workspace name and user role for the very first user.

    NB: When the very first user is created, the very first workspace is also created
    and the API limits for that workspace is updated.

    The process is as follows:

    1. Create the very first workspace for the very first user. No quotas are set, the
        user role defaults to ADMIN and the workspace name defaults to
        `default_workspace_name`.
    2. Add the very first user to the default workspace with the ADMIN role.
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
    assert (users_exist and workspaces_exist) or not (users_exist and workspaces_exist)
    if users_exist and workspaces_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There are already users assigned to workspaces.",
        )

    # 1.
    user.role = UserRoles.ADMIN
    user.workspace_name = default_workspace_name
    workspace_db_new = await create_workspace(
        api_daily_quota=None,
        asession=asession,
        content_quota=None,
        workspace_name=user.workspace_name,
    )

    # 2.
    user_new = await add_user_to_workspace(
        asession=asession, user=user, workspace_db=workspace_db_new
    )

    # 3.
    await update_api_limits(
        api_daily_quota=workspace_db_new.api_daily_quota,
        redis=request.app.state.redis,
        workspace_name=workspace_db_new.workspace_name,
    )

    return user_new


@router.get("/", response_model=list[UserRetrieve])
async def retrieve_all_users(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[UserRetrieve]:
    """Return a list of all user objects.

    NB: When this endpoint called, it **should** be called by ADMIN users only since
    details about users and workspaces are returned.

    The process is as follows:

    1. If the calling user is not an admin in any workspace, then no user or workspace
        information is returned.
    2. If the calling user is an admin in one or more workspaces, then the details for
        all workspaces are returned.

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

    calling_user_workspace_roles = await get_user_role_in_all_workspaces(
        asession=asession, user_db=calling_user_db
    )
    user_mapping: dict[str, UserRetrieve] = {}
    for row in calling_user_workspace_roles:
        if row.user_role != UserRoles.ADMIN:  # Critical!
            continue
        workspace_name = row.workspace_name
        user_workspace_roles = await get_users_and_roles_by_workspace_name(
            asession=asession, workspace_name=workspace_name
        )
        for uwr in user_workspace_roles:
            if uwr.username not in user_mapping:
                user_mapping[uwr.username] = UserRetrieve(
                    created_datetime_utc=uwr.created_datetime_utc,
                    updated_datetime_utc=uwr.updated_datetime_utc,
                    username=uwr.username,
                    user_id=uwr.user_id,
                    user_workspace_names=[workspace_name],
                    user_workspace_roles=[uwr.user_role.value],
                )
            else:
                user_data = user_mapping[uwr.username]
                user_data.user_workspace_names.append(workspace_name)
                user_data.user_workspace_roles.append(uwr.user_role.value)
    return list(user_mapping.values())


@router.put("/rotate-key", response_model=KeyResponse)
async def get_new_api_key(
    workspace_db: Annotated[WorkspaceDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> KeyResponse:
    """Generate a new API key for the workspace. Takes a workspace object, generates a
    new key, replaces the old one in the database, and returns a workspace object with
    the new key.

    Parameters
    ----------
    workspace_db
        The workspace object requesting the new API key.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    KeyResponse
        The response object containing the new API key.

    Raises
    ------
    HTTPException
        If there is an error updating the workspace API key.
    """

    new_api_key = generate_key()

    try:
        # This is necessary to attach the `workspace_db` object to the session.
        asession.add(workspace_db)
        workspace_db_updated = await update_workspace_api_key(
            asession=asession, new_api_key=new_api_key, workspace_db=workspace_db
        )
        return KeyResponse(
            new_api_key=new_api_key, workspace_name=workspace_db_updated.workspace_name
        )
    except SQLAlchemyError as e:
        logger.error(f"Error updating workspace API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating workspace API key.",
        ) from e


@router.get("/require-register", response_model=RequireRegisterResponse)
async def is_register_required(
    asession: AsyncSession = Depends(get_async_session)
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
    user: UserResetPassword,
    asession: AsyncSession = Depends(get_async_session),
) -> UserRetrieve:
    """Reset user password. Takes a user object, generates a new password, replaces the
    old one in the database, and returns the updated user object.

    NB: When this endpoint is called, the assumption is that the calling user is an
    admin user and can only reset passwords for users within their workspaces. Since
    the `retrieve_all_users` endpoint is invoked first to display the correct users for
    the calling user's workspaces, there should be no issue with a non-admin user
    resetting passwords for users in other workspaces.

    Parameters
    ----------
    user
        The user object with the new password and recovery code.
    asession
        The async session to use for the database connection.

    Returns
    -------
    UserRetrieve
        The updated user object.

    Raises
    ------
    HTTPException
        If the user is not found or if the recovery code is incorrect
    """

    try:
        user_to_update = await get_user_by_username(
            asession=asession, username=user.username
        )
        if user.recovery_code not in user_to_update.recovery_codes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recovery code is incorrect.",
            )
        updated_recovery_codes = [
            val for val in user_to_update.recovery_codes if val != user.recovery_code
        ]
        updated_user = await reset_user_password_in_db(
            asession=asession,
            user=user,
            user_id=user_to_update.user_id,
            recovery_codes=updated_recovery_codes,
        )
        updated_user_workspace_roles = await get_user_role_in_all_workspaces(
            asession=asession, user_db=updated_user
        )
        return UserRetrieve(
            created_datetime_utc=updated_user.created_datetime_utc,
            updated_datetime_utc=updated_user.updated_datetime_utc,
            username=updated_user.username,
            user_id=updated_user.user_id,
            user_workspace_names=[
                row.workspace_name for row in updated_user_workspace_roles
            ],
            user_workspace_roles=[
                row.user_role for row in updated_user_workspace_roles
            ],
        )
    except UserNotFoundError as e:
        logger.error(f"Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        ) from e


@router.put("/{user_id}", response_model=UserRetrieve)
async def update_user(
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    user_id: int,
    user: UserCreate,
    asession: AsyncSession = Depends(get_async_session),
) -> UserRetrieve:
    """Update the user's name and/or role in a workspace.

    NB: When this endpoint is called, the assumption is that the calling user is an
    admin user and can only update user information for users within their workspaces.
    Since the `retrieve_all_users` endpoint is invoked first to display the correct
    users for the calling user's workspaces, there should be no issue with a non-admin
    user updating user information in other workspaces.

    NB: A user's API daily quota limit and content quota can no longer be updated since
    these are set at the workspace level when the workspace is first created by the
    calling (admin) user. Instead, the workspace should be updated to reflect these
    changes.

    NB: If the user's role is being updated, then the workspace name must also be
    specified (and vice versa). In addition, the calling user must be an admin user and
    have the appropriate privileges in the workspace that is being updated.

    The process is as follows:

    1. If `UserCreate` contains both a workspace name and workspace role, then the
        update procedure will update the user's role in that workspace.
    2. Update the user's name in the database.

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

    Raises
    ------
    HTTPException
        If the user to update is not found.
        If the username is already taken.
    """

    updated_user_workspace_name = user.workspace_name
    updated_user_workspace_role = user.role
    assert not (updated_user_workspace_name and updated_user_workspace_role) or (
        updated_user_workspace_name and updated_user_workspace_role
    )
    try:
        user_db = await get_user_by_id(user_id=user_id, asession=asession)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User ID {user_id} not found.",
        )
    if user.username != user_db.username and not await is_username_valid(
        asession=asession, username=user.username
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with username {user.username} already exists.",
        )

    # 1.
    if updated_user_workspace_name:
        workspace_db = await get_workspace_by_workspace_name(
            asession=asession, workspace_name=updated_user_workspace_name
        )
        current_user_workspace_role = await get_user_role_in_workspace(
            asession=asession, user_db=calling_user_db, workspace_db=workspace_db
        )
        assert current_user_workspace_role == UserRoles.ADMIN  # Should not be necessary
        await update_user_role_in_workspace(
            asession=asession,
            new_role=user.role,
            user_db=user_db,
            workspace_db=workspace_db,
        )

    # 2.
    updated_user_db = await update_user_in_db(
        asession=asession, user=user, user_id=user_id
    )

    updated_user_workspace_roles = await get_user_role_in_all_workspaces(
        asession=asession, user_db=user_db
    )
    return UserRetrieve(
        created_datetime_utc=updated_user_db.created_datetime_utc,
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

    NB: When this endpoint is called, the assumption is that the calling user is an
    admin user and has access to the user object.

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
        updated_datetime_utc=user_db.updated_datetime_utc,
        user_id=user_db.user_id,
        username=user_db.username,
        user_workspace_names=[row.workspace_name for row in user_workspace_roles],
        user_workspace_roles=[row.user_role.value for row in user_workspace_roles],
    )


async def add_user_to_workspace(
    *,
    asession: AsyncSession,
    user: UserCreate | UserCreateWithPassword,
    workspace_db: WorkspaceDB,
) -> UserCreateWithCode:
    """The process for adding a user to a workspace is:

    1. Generate recovery codes for the user.
    2. Save the user to the `UserDB` database along with their recovery codes.
    3. Add the user to the workspace with the specified role.

    NB: If this function is invoked, then the assumption is that it is called by an
    ADMIN user with access to the specified workspace and that this ADMIN user is
    adding a **new** user to the workspace with the specified user role.

    NB: We do not update the API limits for the workspace when a new user is added to
    the workspace. This is because the API limits are set at the workspace level when
    the workspace is first created by the admin and not at the user level.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user
        The user object to use for adding the user to the workspace.
    workspace_db
        The workspace object to use.

    Returns
    -------
    UserCreateWithCode
        The user object with the recovery codes.
    """

    # 1.
    recovery_codes = generate_recovery_codes()

    # 2.
    user_db = await save_user_to_db(
        asession=asession, recovery_codes=recovery_codes, user=user
    )

    # 3.
    _ = await add_user_workspace_role(
        asession=asession,
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
