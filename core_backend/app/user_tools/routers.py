"""This module contains the FastAPI router for user creation and registration
endpoints.
"""

from typing import Annotated, Optional

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
    add_user_workspace_role,
    check_if_users_exist,
    check_if_workspaces_exist,
    create_workspace,
    get_all_users,
    get_user_by_id,
    get_user_by_username,
    is_username_valid,
    reset_user_password_in_db,
    save_user_to_db,
    update_user_api_key,
    update_user_in_db,
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
    user: UserCreateWithPassword,
    request: Request,
    asession: AsyncSession = Depends(get_async_session),
) -> UserCreateWithCode:
    """Create user endpoint. Can only be used by ADMIN users.

    NB: If this endpoint is invoked, then the assumption is that the user that invoked
    the endpoint is already an ADMIN user with access to appropriate workspaces. In
    other words, the frontend needs to ensure that user creation can only be done by
    ADMIN users in the workspaces that the ADMIN users belong to.

    Parameters
    ----------
    user
        The user object to create.
    request
        The request object.
    asession
        The async session to use for the database connection.

    Returns
    -------
    UserCreateWithCode
        The user object with the recovery codes.

    Raises
    ------
    HTTPException
        If the user already exists or if the user already exists in the workspace.
    """

    try:
        # The hack fix here assumes that the user that invokes this endpoint is an
        # ADMIN user in the "SUPER ADMIN" workspace. Thus, the user is allowed to add a
        # new user only to the "SUPER ADMIN" workspace. In this case, the new user is
        # added as a READ ONLY user to the "SUPER ADMIN" workspace but the user could
        # also choose to add the new user as an ADMIN user in the "SUPER ADMIN"
        # workspace.
        user_new = await add_user_to_workspace(
            asession=asession,
            request=request,
            user=user,
            user_role=UserRoles.READ_ONLY,
            workspace_name="SUPER ADMIN",
        )
        return user_new
    except UserAlreadyExistsError as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with that username already exists.",
        ) from e
    except UserWorkspaceRoleAlreadyExistsError as e:
        logger.error(f"Error creating user in workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with that username already exists in the specified workspace.",
        ) from e



@router.post("/register-first-user", response_model=UserCreateWithCode)
async def create_first_user(
    user: UserCreateWithPassword,
    request: Request,
    asession: AsyncSession = Depends(get_async_session),
) -> UserCreateWithCode:
    """Create the first ADMIN user when there are no users in the `UserDB` table.

    Parameters
    ----------
    user
        The user object to create.
    request
        The request object.
    asession
        The async session to use for the database connection.

    Returns
    -------
    UserCreateWithCode
        The user object with the recovery codes.

    Raises
    ------
    HTTPException
        If there are already ADMIN users in the database.
    """

    users_exist = await check_if_users_exist(asession=asession)
    workspaces_exist = await check_if_workspaces_exist(asession=asession)
    assert (users_exist and workspaces_exist) or not (users_exist and workspaces_exist)
    if users_exist and workspaces_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There are already users in the database.",
        )

    # Create the default workspace for the very first user and assign the user as an
    # ADMIN.
    user_new = await add_user_to_workspace(
        asession=asession,
        request=request,
        user=user,
        user_role=UserRoles.ADMIN,
        workspace_name="SUPER ADMIN",
    )
    return user_new


@router.get("/", response_model=list[UserRetrieve])
async def retrieve_all_users(
    asession: AsyncSession = Depends(get_async_session)
) -> list[UserRetrieve]:
    """Return a list of all user objects.

    Parameters
    ----------
    asession
        The async session to use for the database connection.

    Returns
    -------
    list[UserRetrieve]
        A list of user objects.
    """

    users = await get_all_users(asession=asession)
    return [
        UserRetrieve(
            created_datetime_utc=user.created_datetime_utc,
            updated_datetime_utc=user.updated_datetime_utc,
            user_id=user.user_id,
            username=user.username,
        )
        for user in users
    ]


@router.put("/rotate-key", response_model=KeyResponse)
async def get_new_api_key(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> KeyResponse | None:
    """
    Generate a new API key for the requester's account. Takes a user object,
    generates a new key, replaces the old one in the database, and returns
    a user object with the new key.
    """

    print("def get_new_api_key")
    input()
    new_api_key = generate_key()

    try:
        # this is neccesarry to attach the user_db to the session
        asession.add(user_db)
        await update_user_api_key(
            user_db=user_db,
            new_api_key=new_api_key,
            asession=asession,
        )
        return KeyResponse(
            username=user_db.username,
            new_api_key=new_api_key,
        )
    except SQLAlchemyError as e:
        logger.error(f"Error updating user api key: {e}")
        raise HTTPException(
            status_code=500, detail="Error updating user api key"
        ) from e


@router.get("/require-register", response_model=RequireRegisterResponse)
async def is_register_required(
    asession: AsyncSession = Depends(get_async_session),
) -> RequireRegisterResponse:
    """Check if there are any SUPER ADMIN users in the database. If there are no
    SUPER ADMIN users, then an initial registration as a SUPER ADMIN user is required.

    Parameters
    ----------
    asession
        The async session to use for the database connection.

    Returns
    -------
    RequireRegisterResponse
        The response object containing the boolean value for whether a SUPER ADMIN user
    registration is required.
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
            user_id=user_to_update.user_id,
            user=user,
            recovery_codes=updated_recovery_codes,
            asession=asession,
        )
        return UserRetrieve(
            user_id=updated_user.user_id,
            username=updated_user.username,
            content_quota=updated_user.content_quota,
            api_daily_quota=updated_user.api_daily_quota,
            is_admin=updated_user.is_admin,
            api_key_first_characters=updated_user.api_key_first_characters,
            api_key_updated_datetime_utc=updated_user.api_key_updated_datetime_utc,
            created_datetime_utc=updated_user.created_datetime_utc,
            updated_datetime_utc=updated_user.updated_datetime_utc,
        )
    except UserNotFoundError as v:
        logger.error(f"Error resetting password: {v}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        ) from v


@router.put("/{user_id}", response_model=UserRetrieve)
async def update_user(
    user_id: int,
    user: UserCreate,
    asession: AsyncSession = Depends(get_async_session),
) -> UserRetrieve | None:
    """
    Update user endpoint.
    """

    print("def update_user")
    input()
    user_db = await get_user_by_id(user_id=user_id, asession=asession)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.username != user_db.username:
        if not await is_username_valid(user.username, asession):
            raise HTTPException(
                status_code=400,
                detail=f"User with username {user.username} already exists.",
            )

    updated_user = await update_user_in_db(
        user_id=user_id, user=user, asession=asession
    )
    return UserRetrieve(
        user_id=updated_user.user_id,
        username=updated_user.username,
        content_quota=updated_user.content_quota,
        api_daily_quota=updated_user.api_daily_quota,
        is_admin=updated_user.is_admin,
        api_key_first_characters=updated_user.api_key_first_characters,
        api_key_updated_datetime_utc=updated_user.api_key_updated_datetime_utc,
        created_datetime_utc=updated_user.created_datetime_utc,
        updated_datetime_utc=updated_user.updated_datetime_utc,
    )


@router.get("/current-user", response_model=UserRetrieve)
async def get_user(
    user_db: Annotated[UserDB, Depends(get_current_user)],
) -> UserRetrieve | None:
    """
    Get user endpoint. Returns the user object for the requester.
    """

    print("def get_user")
    input()
    return UserRetrieve(
        user_id=user_db.user_id,
        username=user_db.username,
        content_quota=user_db.content_quota,
        api_daily_quota=user_db.api_daily_quota,
        is_admin=user_db.is_admin,
        api_key_first_characters=user_db.api_key_first_characters,
        api_key_updated_datetime_utc=user_db.api_key_updated_datetime_utc,
        created_datetime_utc=user_db.created_datetime_utc,
        updated_datetime_utc=user_db.updated_datetime_utc,
    )


async def add_user_to_workspace(
    *,
    api_daily_quota: Optional[int] = None,
    asession: AsyncSession,
    content_quota: Optional[int] = None,
    request: Request,
    user: UserCreate | UserCreateWithPassword,
    user_role: UserRoles,
    workspace_name: str,
) -> UserCreateWithCode:
    """Generate recovery codes for the user, save user to the `UserDB` database, and
    update the API limits for the user. Also add the user to the specified workspace.

    NB: If this function is invoked, then the assumption is that it is called by an
    ADMIN user with access to the specified workspace and that this ADMIN user is
    adding a new user to the workspace with the specified user role.

    Parameters
    ----------
    api_daily_quota
        The daily API quota for the workspace.
    asession
        The async session to use for the database connection.
    content_quota
        The content quota for the workspace.
    request
        The request object.
    user
        The user object to use.
    user_role
        The role of the user in the workspace.
    workspace_name
        The name of the workspace to create.

    Returns
    -------
    UserCreateWithCode
        The user object with the recovery codes.
    """

    # Save user to `UserDB` table with recovery codes.
    recovery_codes = generate_recovery_codes()
    user_new = await save_user_to_db(
        asession=asession, recovery_codes=recovery_codes, user=user
    )

    # Create the workspace.
    workspace_new = await create_workspace(
        api_daily_quota=api_daily_quota,
        asession=asession,
        content_quota=content_quota,
        workspace_name=workspace_name,
    )

    # Assign user to the specified workspace with the specified role.
    _ = await add_user_workspace_role(
        asession=asession, user=user_new, user_role=user_role, workspace=workspace_new
    )

    # Update workspace API quota.
    await update_api_limits(
        api_daily_quota=workspace_new.api_daily_quota,
        redis=request.app.state.redis,
        workspace_name=workspace_new.workspace_name,
    )

    return UserCreateWithCode(recovery_codes=recovery_codes, username=user_new.username)
