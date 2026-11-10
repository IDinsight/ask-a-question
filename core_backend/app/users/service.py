"""This module contains the business logic for user creation, registration, retrieval,
update and removal.

Route handlers in `app.users.router` delegate to the functions here. Functions in this
module never raise `HTTPException`; they raise the domain exceptions in
`app.core.exceptions`, which the global exception handler converts into the same
`{"detail": ...}` responses.
"""

import os
from typing import Sequence

import sqlalchemy
from redis import asyncio as aioredis
from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
)
from app.core.observability import setup_logger
from app.core.security import update_api_limits
from app.question_answer.schemas import IdentifiedLanguage
from app.users.models import UserDB
from app.users.repository import (
    UserNotFoundError,
    UserNotFoundInWorkspaceError,
    UserWorkspaceRoleAlreadyExistsError,
    add_existing_user_to_workspace,
    add_new_user_to_workspace,
    check_if_two_users_share_a_common_workspace,
    check_if_user_exists,
    check_if_user_exists_in_workspace,
    check_if_users_exist,
    get_admin_users_in_workspace,
    get_user_by_id,
    get_user_role_in_all_workspaces,
    get_user_role_in_workspace,
    get_users_and_roles_by_workspace_id,
    get_workspaces_by_user_role,
    is_username_valid,
    remove_user_from_dbs,
    reset_user_password_in_db,
    update_user_default_workspace,
    update_user_in_db,
    update_user_role_in_workspace,
    user_has_admin_role_in_any_workspace,
    user_has_required_role_in_workspace,
    users_exist_in_workspace,
)
from app.users.schemas import (
    RequireRegisterResponse,
    UserCreate,
    UserCreateWithCode,
    UserCreateWithPassword,
    UserRemoveResponse,
    UserResetPassword,
    UserRetrieve,
    UserRoles,
    UserUpdate,
    UserWorkspace,
)
from app.workspaces.models import WorkspaceDB
from app.workspaces.repository import (
    WorkspaceNotFoundError,
    check_if_workspaces_exist,
    create_workspace,
    get_workspace_by_workspace_name,
)

logger = setup_logger()


async def create_user_in_workspace(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    user: UserCreateWithPassword,
) -> UserCreateWithCode:
    """Create a new user in an existing workspace.

    The process is as follows:

    1. If the username already exists, then raise a 400 error.
    2. The rest of the parameters for creating a new user in a workspace are checked.
    3. Create the new user and add the user to the specified workspace with the
        specified role. The specified workspace is also set as the new user's default
        workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is creating a new user.
    user
        The user object to create.

    Returns
    -------
    UserCreateWithCode
        The user object with the recovery codes.

    Raises
    ------
    BadRequestError
        If the username already exists.
    """

    # 1.
    if await check_if_user_exists(asession=asession, user=user):
        raise BadRequestError("Username already exists.")

    # 2.
    user_checked, user_checked_workspace_db = await check_create_or_add_user_call(
        asession=asession, calling_user_db=calling_user_db, user=user
    )
    assert isinstance(user_checked, UserCreateWithPassword)
    assert user_checked.workspace_name

    # 3.
    return await add_new_user_to_workspace(
        asession=asession, user=user_checked, workspace_db=user_checked_workspace_db
    )


async def add_user_to_workspace(
    *, asession: AsyncSession, calling_user_db: UserDB, user: UserCreate
) -> UserCreateWithCode:
    """Add an existing user to an existing workspace.

    The process is as follows:

    1. If the user does not exist, then raise a 404 error.
    2. The rest of the parameters for adding an existing user to a workspace are
        checked.
    3. Add the existing user to the specified workspace with the specified role.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is adding an existing user.
    user
        The user object to add.

    Returns
    -------
    UserCreateWithCode
        The user object with the recovery codes.

    Raises
    ------
    NotFoundError
        If the username does not exist.
    BadRequestError
        If the user is already assigned a role in the specified workspace.
    """

    # 1.
    if not await check_if_user_exists(asession=asession, user=user):
        raise NotFoundError("Username does not exist.")

    # 2.
    user_checked, user_checked_workspace_db = await check_create_or_add_user_call(
        asession=asession, calling_user_db=calling_user_db, user=user
    )
    assert not isinstance(user_checked, UserCreateWithPassword) and isinstance(
        user_checked, UserCreate
    )
    assert user_checked.workspace_name

    # 3.
    try:
        return await add_existing_user_to_workspace(
            asession=asession, user=user_checked, workspace_db=user_checked_workspace_db
        )
    except UserWorkspaceRoleAlreadyExistsError as e:
        logger.error(f"Error creating user workspace role: {e}")
        raise BadRequestError("User workspace role already exists.") from e


async def register_first_user(
    *, asession: AsyncSession, redis: aioredis.Redis, user: UserCreateWithPassword
) -> UserCreateWithCode:
    """Create the very first user (as an ADMIN) together with their first workspace.

    The process is as follows:

    1. Create the very first workspace for the very first user. No quotas are set, the
        default document language is set, and the user role defaults to ADMIN.
    2. Add the very first user to the default workspace with the ADMIN role and assign
        the workspace as the default workspace for the first user.
    3. Update the API limits for the workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    redis
        The Redis instance used to store API limits.
    user
        The object to use for user creation. NB: `user.role` and `user.workspace_name`
        are updated in place.

    Returns
    -------
    UserCreateWithCode
        The created user object with the recovery codes.

    Raises
    ------
    BadRequestError
        If there are already users assigned to workspaces.
    """

    users_exist = await check_if_users_exist(asession=asession)
    workspaces_exist = await check_if_workspaces_exist(asession=asession)
    if users_exist and workspaces_exist:
        raise BadRequestError("There are already users assigned to workspaces.")

    # 1.
    default_doc_language = os.getenv("DEFAULT_DOC_LANGUAGE", IdentifiedLanguage.ENGLISH)
    user.role = UserRoles.ADMIN
    user.workspace_name = user.workspace_name or f"{user.username}'s Workspace"
    workspace_db_new, _ = await create_workspace(
        asession=asession, doc_language=default_doc_language, user=user
    )

    # 2.
    user_new = await add_new_user_to_workspace(
        asession=asession, user=user, workspace_db=workspace_db_new
    )

    # 3.
    await update_api_limits(
        api_daily_quota=workspace_db_new.api_daily_quota,
        redis=redis,
        workspace_name=workspace_db_new.workspace_name,
    )

    return user_new


async def delete_user_from_workspace(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    remove_from_workspace_name: str,
    user_id: int,
    workspace_name: str,
) -> UserRemoveResponse:
    """Remove a user from a workspace and work out what the frontend must do next.

    The process is as follows:

    1. If the user is assigned to the specified workspace, then the user (and their
        role) is removed from that workspace. If the specified workspace was the user's
        default workspace, then the next workspace that the user is assigned to is set
        as the user's default workspace.
    2. If the user is not assigned to any workspace after being removed from the
        specified workspace, then the user is also deleted from the `UserDB` database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is removing the user.
    remove_from_workspace_name
        The name of the workspace from which the user is being removed.
    user_id
        The user ID to remove from the specified workspace.
    workspace_name
        The name of the workspace that the calling user is currently logged into.

    Returns
    -------
    UserRemoveResponse
        The response object with the user's default workspace name after removal and
        the workspace from which they were removed.

    Raises
    ------
    NotFoundError
        If the user is not found in the workspace to be removed from.
    InternalServerError
        If the deletion violates a database integrity constraint.
    """

    remove_from_workspace_db, user_db = await check_remove_user_from_workspace_call(
        asession=asession,
        calling_user_db=calling_user_db,
        remove_from_workspace_name=remove_from_workspace_name,
        user_id=user_id,
    )

    # 1 and 2.
    try:
        (
            default_workspace_name,
            removed_from_workspace_name,
        ) = await remove_user_from_dbs(
            asession=asession,
            remove_from_workspace_db=remove_from_workspace_db,
            user_db=user_db,
        )
    except UserNotFoundInWorkspaceError as e:
        raise NotFoundError("User not found in workspace.") from e
    except sqlalchemy.exc.IntegrityError as e:
        logger.error(f"Error deleting content: {e}")
        raise InternalServerError(
            "Deletion of content with feedback is not allowed."
        ) from e

    # A user removing themselves from their only workspace must re-authenticate; a
    # user removing themselves from the workspace they are logged into must switch
    # workspaces. Re-authentication implies a workspace switch.
    self_removal = calling_user_db.user_id == user_id
    require_authentication = self_removal and default_workspace_name is None
    require_workspace_switch = require_authentication or (
        self_removal and removed_from_workspace_name == workspace_name
    )
    return UserRemoveResponse(
        default_workspace_name=default_workspace_name,
        removed_from_workspace_name=removed_from_workspace_name,
        require_authentication=require_authentication,
        require_workspace_switch=require_workspace_switch,
    )


async def list_users_in_workspace(
    *, asession: AsyncSession, calling_user_db: UserDB, workspace_name: str
) -> list[UserRetrieve]:
    """Return the users visible to the calling user in the current workspace.

    The process is as follows:

    1. If the calling user is an admin in the current workspace, then the details of
        all users in the current workspace are returned.
    2. Otherwise, only the details of the calling user is returned.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is retrieving the list of users.
    workspace_name
        The name of the workspace that the calling user is currently logged into.

    Returns
    -------
    list[UserRetrieve]
        A list of retrieved user objects.

    Raises
    ------
    InternalServerError
        If the calling user has no role in the current workspace.
    ForbiddenError
        If the calling user does not have the required role to retrieve users in the
        current workspace.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    workspace_id = workspace_db.workspace_id
    calling_user_role_in_workspace = await get_user_role_in_workspace(
        asession=asession, user_db=calling_user_db, workspace_db=workspace_db
    )

    match calling_user_role_in_workspace:
        # 1.
        case UserRoles.ADMIN:
            # Group the (user, role) rows by username so each user appears once.
            user_mapping: dict[str, UserRetrieve] = {}
            user_workspace_roles = await get_users_and_roles_by_workspace_id(
                asession=asession, workspace_id=workspace_id
            )
            for uwr in user_workspace_roles:
                if uwr.username not in user_mapping:
                    user_mapping[uwr.username] = UserRetrieve(
                        created_datetime_utc=uwr.created_datetime_utc,
                        is_default_workspace=[uwr.default_workspace],
                        updated_datetime_utc=uwr.updated_datetime_utc,
                        user_id=uwr.user_id,
                        user_workspaces=[
                            UserWorkspace(
                                user_role=uwr.user_role.value,
                                workspace_id=workspace_id,
                                workspace_name=workspace_name,
                            )
                        ],
                        username=uwr.username,
                    )
                else:
                    user_data = user_mapping[uwr.username]
                    user_data.is_default_workspace.append(uwr.default_workspace)
                    user_data.user_workspaces.append(
                        UserWorkspace(
                            user_role=uwr.user_role.value,
                            workspace_id=workspace_id,
                            workspace_name=workspace_name,
                        )
                    )
            user_list = list(user_mapping.values())
        # 2.
        case UserRoles.READ_ONLY:
            calling_user_workspace_roles = await get_user_role_in_all_workspaces(
                asession=asession, user_db=calling_user_db
            )
            user_list = [
                _convert_user_db_to_user_retrieve(
                    user_db=calling_user_db,
                    user_workspace_roles=calling_user_workspace_roles,
                )
            ]
        case None:
            raise InternalServerError("Calling user role in workspace is `None`.")
        case _:
            raise ForbiddenError(
                "Calling user does not have the required role to retrieve users "
                "in the current workspace."
            )

    return user_list


async def check_register_required(*, asession: AsyncSession) -> RequireRegisterResponse:
    """Determine whether initial registration is required.

    Registration is required if there are neither users nor workspaces in the
    `UserDB` and `WorkspaceDB` databases.

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


async def reset_user_password(
    *, asession: AsyncSession, user: UserResetPassword
) -> UserRetrieve:
    """Reset a user's password using one of their recovery codes.

    The process is as follows:

    1. The user password is reset in the `UserDB` database and the used recovery code
        is discarded.
    2. The user's role in all workspaces is retrieved for the return object.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user
        The user object with the new password and recovery code.

    Returns
    -------
    UserRetrieve
        The updated user object.
    """

    user_to_update = await check_reset_password_call(asession=asession, user=user)

    # 1. Recovery codes are single-use, so drop the one that was just used.
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

    return _convert_user_db_to_user_retrieve(
        user_db=updated_user_db, user_workspace_roles=updated_user_workspace_roles
    )


async def update_user_details(
    *, asession: AsyncSession, calling_user_db: UserDB, user: UserUpdate, user_id: int
) -> UserRetrieve:
    """Update a user's name, role in a workspace, and/or their default workspace.

    The process is as follows:

    1. Parameters for the call are checked first.
    2. If the user's workspace role is being updated, then the user's role in that
        workspace is updated.
    3. Update the user's default workspace.
    4. Update the user's name in the database.
    5. Retrieve the updated user's role in all workspaces for the return object.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user updating the user.
    user
        The user object with the updated information.
    user_id
        The user ID to update.

    Returns
    -------
    UserRetrieve
        The updated user object.

    Raises
    ------
    NotFoundError
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
            raise NotFoundError(f"User ID '{user_id}' not found in workspace.") from e

    # 3.
    if user.is_default_workspace and user.workspace_name and workspace_db_checked:
        try:
            await update_user_default_workspace(
                asession=asession,
                user_db=user_db_checked,
                workspace_db=workspace_db_checked,
            )
        except UserNotFoundInWorkspaceError as e:
            raise NotFoundError(f"User ID '{user_id}' not found in workspace.") from e

    # 4.
    updated_user_db = await update_user_in_db(
        asession=asession, user=user, user_id=user_id
    )

    # 5.
    updated_user_workspace_roles = await get_user_role_in_all_workspaces(
        asession=asession, user_db=updated_user_db
    )

    return _convert_user_db_to_user_retrieve(
        user_db=updated_user_db, user_workspace_roles=updated_user_workspace_roles
    )


async def get_user_details(*, asession: AsyncSession, user_db: UserDB) -> UserRetrieve:
    """Retrieve the user object, with roles in all workspaces, for the given user.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_db
        The user object associated with the user that is being retrieved.

    Returns
    -------
    UserRetrieve
        The retrieved user object.
    """

    user_workspace_roles = await get_user_role_in_all_workspaces(
        asession=asession, user_db=user_db
    )
    return _convert_user_db_to_user_retrieve(
        user_db=user_db, user_workspace_roles=user_workspace_roles
    )


async def check_username_exists(
    *, asession: AsyncSession, calling_user_db: UserDB, username: str
) -> None:
    """Check that the calling user may look up usernames and that `username` exists.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is checking the username.
    username
        The username to check.

    Raises
    ------
    ForbiddenError
        If the calling user does not have the correct role to check if a username
        exists.
    NotFoundError
        If the username does not exist.
    """

    if not await user_has_admin_role_in_any_workspace(
        asession=asession, user_db=calling_user_db
    ):
        raise ForbiddenError(
            "Calling user does not have the correct role to check if a username "
            "exists."
        )

    if not await check_if_user_exists(
        asession=asession, user=UserCreate(username=username)
    ):
        # NB: `HTTPException(status_code=404)` without a detail defaults to the HTTP
        # status phrase, so the same detail is used here.
        raise NotFoundError("Not Found")


async def check_remove_user_from_workspace_call(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    remove_from_workspace_name: str,
    user_id: int,
) -> tuple[WorkspaceDB, UserDB]:
    """Check the remove user from workspace call to ensure the action is allowed.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is removing the user from the
        specified workspace.
    remove_from_workspace_name
        The name of the workspace from which the user is being removed.
    user_id
        The user ID to remove from the specified workspace.

    Returns
    -------
    tuple[WorkspaceDB, UserDB]
        The workspace and user objects to remove the user from.

    Raises
    ------
    BadRequestError
        If the workspace to remove the user from does not exist.
    ForbiddenError
        If the user does not have the required role to remove users from the specified
        workspace.
        If the user is attempting to remove the last admin user from the specified
        workspace.
    NotFoundError
        If the user ID is not found.
    """

    try:
        remove_from_workspace_db = await get_workspace_by_workspace_name(
            asession=asession, workspace_name=remove_from_workspace_name
        )
    except WorkspaceNotFoundError as e:
        raise BadRequestError(
            f"Workspace does not exist: {remove_from_workspace_name}"
        ) from e

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=remove_from_workspace_db,
    ):
        raise ForbiddenError(
            "User does not have the required role to remove users from the "
            "specified workspace."
        )

    user_db = await get_user_by_id(asession=asession, user_id=user_id)

    if not user_db:
        raise NotFoundError(f"User ID `{user_id}` not found.")

    # Every workspace must keep at least one ADMIN user.
    workspace_admin_dbs = await get_admin_users_in_workspace(
        asession=asession, workspace_id=remove_from_workspace_db.workspace_id
    )
    assert workspace_admin_dbs is not None
    if len(workspace_admin_dbs) == 1 and workspace_admin_dbs[0].user_id == user_id:
        raise ForbiddenError("Cannot remove last admin user from the workspace.")

    return remove_from_workspace_db, user_db


async def check_create_or_add_user_call(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    user: UserCreate | UserCreateWithPassword,
) -> tuple[UserCreate | UserCreateWithPassword, WorkspaceDB]:
    """Check the create/add user call to ensure the action is allowed.

    NB: This function:

    1. Changes `user.workspace_name` to the workspace name of the calling user if it is
        not specified.
    2. Assigns a default role of READ ONLY if the role is not specified.

    The process is as follows:

    1. If a workspace is specified for the user being created/added and the workspace is
        not yet created, then an error is thrown. This is a safety net for the backend
        since the frontend should ensure that a user can only be created in/added to
        existing workspaces.
    2. If the calling user is not an admin in any workspace, then an error is thrown.
        This is a safety net for the backend since the frontend should ensure that the
        ability to create/add a user is only available to admin users.
    3. If the workspace is not specified for the user and the calling user belongs to
        multiple workspaces, then an error is thrown. This is a safety net for the
        backend since the frontend should ensure that a workspace is specified when
        creating/adding a user if there are multiple workspaces to choose from.
    4. If the calling user is not an admin in the workspace specified for the user and
        the specified workspace exists with users and roles, then an error is thrown.
        In this case, the calling user must be an admin in the specified workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is creating/adding a user.
    user
        The user object to create/add.

    Returns
    -------
    tuple[UserCreate | UserCreateWithPassword, WorkspaceDB]
        The user and workspace objects to create/add.

    Raises
    ------
    BadRequestError
        If a workspace is specified for the user being created/added and the workspace
        is not yet created.
        If the user workspace is not specified and the calling user belongs to multiple
        workspaces.
    ForbiddenError
        If the calling user does not have the correct role to create/add a user in any
        workspace.
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
            raise BadRequestError(
                f"Workspace does not exist: {user.workspace_name}"
            ) from e

    # 2.
    if not await user_has_admin_role_in_any_workspace(
        asession=asession, user_db=calling_user_db
    ):
        raise ForbiddenError(
            "Calling user does not have the correct role to create a user in "
            "any workspace."
        )

    calling_user_admin_workspace_dbs = await get_workspaces_by_user_role(
        asession=asession, user_db=calling_user_db, user_role=UserRoles.ADMIN
    )

    # 3.
    if not user.workspace_name and len(calling_user_admin_workspace_dbs) != 1:
        raise BadRequestError(
            "Calling user belongs to multiple workspaces. A workspace must be "
            "specified for creating a user."
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
            raise ForbiddenError(
                f"Calling user does not have the correct role in the specified "
                f"workspace: {user.workspace_name}"
            )
    else:
        # NB: `user.workspace_name` is updated here!
        user.workspace_name = calling_user_admin_workspace_dbs[0].workspace_name
    assert user.workspace_name is not None

    # NB: `user.role` is updated here!
    user.role = user.role or UserRoles.READ_ONLY

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=user.workspace_name
    )

    return user, workspace_db


async def check_reset_password_call(
    *, asession: AsyncSession, user: UserResetPassword
) -> UserDB:
    """Check the reset password call to ensure the action is allowed.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user
        The user object with the new password and recovery code.

    Returns
    -------
    UserDB
        The user object to update.

    Raises
    ------
    NotFoundError
        If the user to update is not found.
    BadRequestError
        If the recovery code is incorrect.
    """

    user_to_update = await check_if_user_exists(asession=asession, user=user)

    if user_to_update is None:
        raise NotFoundError("User not found.")

    if (
        not user.recovery_code
        or user.recovery_code not in user_to_update.recovery_codes
    ):
        raise BadRequestError("Recovery code is incorrect.")

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
    tuple[UserDB, WorkspaceDB | None]
        The user and workspace objects to update.

    Raises
    ------
    ForbiddenError
        If the calling user does not have the correct access to update the user.
        If the calling user and the user being updated does not share workspaces.
        If the calling user is not an admin in the workspace.
    BadRequestError
        If a user's role is being changed but the workspace name is not specified.
        If a user's default workspace is being changed but the workspace name is not
            specified.
        If the username is already taken.
        If the user does not belong to the specified workspace.
    NotFoundError
        If the user to update is not found.
    """

    if not (
        await user_has_admin_role_in_any_workspace(
            asession=asession, user_db=calling_user_db
        )
        and await check_if_two_users_share_a_common_workspace(
            asession=asession, user_id_1=calling_user_db.user_id, user_id_2=user_id
        )
    ):
        raise ForbiddenError(
            "Calling user does not have the correct role to update user information."
        )

    if user.role and not user.workspace_name:
        raise BadRequestError(
            "Workspace name must be specified if user's role is being updated."
        )

    if user.is_default_workspace is not None and not user.workspace_name:
        raise BadRequestError(
            "Workspace name must be specified if user's default workspace is "
            "being updated."
        )

    try:
        user_db = await get_user_by_id(asession=asession, user_id=user_id)
    except UserNotFoundError as e:
        raise NotFoundError(f"User ID {user_id} not found.") from e

    if user.username != user_db.username and not await is_username_valid(
        asession=asession, username=user.username
    ):
        raise BadRequestError(f"User with username {user.username} already exists.")

    workspace_db = None

    # Assumption here is that if the workspace name is specified when updating a user,
    # then the calling user must be an admin in that workspace AND the user being
    # updated must also exist in that workspace.
    if user.workspace_name:
        workspace_db = await get_workspace_by_workspace_name(
            asession=asession, workspace_name=user.workspace_name
        )
        calling_user_workspace_role = await get_user_role_in_workspace(
            asession=asession, user_db=calling_user_db, workspace_db=workspace_db
        )

        if calling_user_workspace_role != UserRoles.ADMIN:
            raise ForbiddenError("Calling user is not an admin in the workspace.")

        if not await check_if_user_exists_in_workspace(
            asession=asession,
            user_id=user_db.user_id,
            workspace_id=workspace_db.workspace_id,
        ):
            raise BadRequestError(
                f"User ID '{user_db.user_id}' does belong to workspace ID "
                f"'{workspace_db.workspace_id}'."
            )

    return user_db, workspace_db


def _convert_user_db_to_user_retrieve(
    *,
    user_db: UserDB,
    user_workspace_roles: Sequence[Row[tuple[int, str, bool, UserRoles]]],
) -> UserRetrieve:
    """Build a `UserRetrieve` from a user record and their roles in all workspaces.

    Parameters
    ----------
    user_db
        The user object.
    user_workspace_roles
        Rows of (workspace ID, workspace name, default workspace flag, user role) for
        every workspace the user belongs to, as returned by
        `get_user_role_in_all_workspaces`.

    Returns
    -------
    UserRetrieve
        The user object with their workspaces, roles and default workspace flags.
    """

    return UserRetrieve(
        created_datetime_utc=user_db.created_datetime_utc,
        is_default_workspace=[row.default_workspace for row in user_workspace_roles],
        updated_datetime_utc=user_db.updated_datetime_utc,
        user_id=user_db.user_id,
        username=user_db.username,
        user_workspaces=[
            UserWorkspace(
                user_role=row.user_role,
                workspace_id=row.workspace_id,
                workspace_name=row.workspace_name,
            )
            for row in user_workspace_roles
        ],
    )
