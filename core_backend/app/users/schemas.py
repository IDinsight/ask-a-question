"""This module contains Pydantic models for users."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


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


class UserRemove(BaseModel):
    """Pydantic model for user removal from a workspace.

    1. If the workspace to remove the user from is also the user's default workspace,
        then the next workspace that the user is assigned to is set as the user's
        default workspace.
    2. If the user is not assigned to any workspace after being removed from the
        specified workspace, then the user is also deleted from the `UserDB` database.
        This is necessary because a user must be assigned to at least one workspace.
    """

    remove_workspace_name: str

    model_config = ConfigDict(from_attributes=True)


class UserRemoveResponse(BaseModel):
    """Pydantic model for user removal response.

    Note:

    1. If `default_workspace_name` is `None` upon return, then this means the user was
    removed from all assigned workspaces and was also deleted from the `UserDB`
    database. This situation should require the user to reauthenticate (i.e.,
    `require_authentication` should be set to `True`).

    2. If `require_workspace_login` is `True` upon return, then this means the user was
    removed from the current workspace. This situation should require a workspace
    login. This case should be superceded by the first case.
    """

    default_workspace_name: Optional[str] = None
    removed_from_workspace_name: str
    require_authentication: bool
    require_workspace_login: bool

    model_config = ConfigDict(from_attributes=True)


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
    username: str
    user_workspace_names: list[str]
    user_workspace_roles: list[UserRoles]

    model_config = ConfigDict(from_attributes=True)


class UserResetPassword(BaseModel):
    """Pydantic model for user password reset."""

    password: str
    recovery_code: str
    username: str

    model_config = ConfigDict(from_attributes=True)
