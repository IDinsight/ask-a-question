"""This module contains Pydantic models for user creation, retrieval, and password
reset. Pydantic models for workspace creation and retrieval are also defined here.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserRoles(Enum):
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
    """Pydantic model for user creation."""

    username: str

    model_config = ConfigDict(from_attributes=True)


class UserCreateWithPassword(UserCreate):
    """Pydantic model for user creation."""

    password: str

    model_config = ConfigDict(from_attributes=True)


class UserCreateWithCode(UserCreate):
    """Pydantic model for user creation with recovery codes for user account
    recovery.
    """

    recovery_codes: list[str]

    model_config = ConfigDict(from_attributes=True)


class UserRetrieve(BaseModel):
    """Pydantic model for user retrieval."""

    created_datetime_utc: datetime
    updated_datetime_utc: datetime
    user_id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class UserResetPassword(BaseModel):
    """Pydantic model for user password reset."""

    password: str
    recovery_code: str
    username: str

    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreate(BaseModel):
    """Pydantic model for workspace creation."""

    api_daily_quota: Optional[int] = None
    content_quota: Optional[int] = None
    workspace_name: str

    model_config = ConfigDict(from_attributes=True)


class WorkspaceRetrieve(BaseModel):
    """Pydantic model for workspace retrieval."""

    api_daily_quota: Optional[int] =  None
    api_key_first_characters: Optional[str]
    api_key_updated_datetime_utc: Optional[datetime]
    content_quota: Optional[int] = None
    created_datetime_utc: datetime
    updated_datetime_utc: datetime
    workspace_id: int
    workspace_name: str

    model_config = ConfigDict(from_attributes=True)
