"""This module contains Pydantic models for users."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RequireRegisterResponse(BaseModel):
    """Pydantic model for require registration response."""

    require_register: bool

    model_config = ConfigDict(from_attributes=True)


class UserRoles(str, Enum):
    """Enumeration for user roles.

    There are 2 different types of users:

    1. (Read-Only) Users: These users are assigned to workspaces and can only read the
         contents within their assigned workspaces. They cannot modify existing
         contents or add new contents to their workspaces, add or delete users from
         their workspaces, or add or delete workspaces.
    2. Admin Users: These users are assigned to workspaces and can read and modify the
         contents within their assigned workspaces. They can also add or delete users
         from their own workspaces and can also add new workspaces or delete their own
         workspaces. Admin users have no control over workspaces that they are not
        assigned to.
    """

    ADMIN = "admin"
    READ_ONLY = "read_only"


class UserCreate(BaseModel):
    """Pydantic model for user creation.

    NB: When a user is created, the user must be assigned to a workspace and a role
    within that workspace. The only exception is if the user is the first user to be
    created, in which case the user will be assigned to a default workspace with a role
    of "ADMIN".
    """

    is_default_workspace: Optional[bool] = None
    role: Optional[UserRoles] = None
    username: str
    workspace_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreateWithPassword(UserCreate):
    """Pydantic model for user creation with a password."""

    password: str

    model_config = ConfigDict(from_attributes=True)


class UserCreateWithCode(UserCreate):
    """Pydantic model for user creation with recovery codes for user account
    recovery.
    """

    recovery_codes: list[str]

    model_config = ConfigDict(from_attributes=True)


class UserRemoveResponse(BaseModel):
    """Pydantic model for user removal response.

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
    """

    default_workspace_name: Optional[str] = None
    removed_from_workspace_name: str
    require_authentication: bool
    require_workspace_switch: bool

    model_config = ConfigDict(from_attributes=True)


class UserResetPassword(BaseModel):
    """Pydantic model for user password reset."""

    password: str
    recovery_code: str
    username: str

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(UserCreate):
    """Pydantic model for updating users.

    In the case of updating an user:

    1. is_default_workspace: If `True` and `workspace_name` is specified, then the
        user's default workspace is updated to the specified workspace.
    2. role: This is the role to update the user to in the specified workspace.
    3. username: The username of the user to update.
    4. workspace_name: The name of the workspace to update the user in. If the field is
        specified and `is_default_workspace` is set to `True`, then the user's default
        workspace is updated to the specified workspace.
    """


class UserWorkspace(BaseModel):
    """Pydantic model for user workspace information."""

    user_role: UserRoles
    workspace_id: int
    workspace_name: str


class UserRetrieve(BaseModel):
    """Pydantic model for user retrieval.

    NB: When a user is retrieved, a mapping between the workspaces that the user
    belongs to and the roles within those workspaces should also be returned. How that
    information is used is up to the caller.
    """

    created_datetime_utc: datetime
    is_default_workspace: list[bool]
    updated_datetime_utc: datetime
    user_id: int
    user_workspaces: list[UserWorkspace]
    username: str

    model_config = ConfigDict(from_attributes=True)
