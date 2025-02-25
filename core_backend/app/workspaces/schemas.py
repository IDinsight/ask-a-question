"""This module contains Pydantic models for workspaces."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from ..config import DEFAULT_API_QUOTA, DEFAULT_CONTENT_QUOTA


class WorkspaceCreate(BaseModel):
    """Pydantic model for workspace creation."""

    api_daily_quota: int | None = DEFAULT_API_QUOTA
    content_quota: int | None = DEFAULT_CONTENT_QUOTA
    workspace_name: str

    model_config = ConfigDict(from_attributes=True)


class WorkspaceKeyResponse(BaseModel):
    """Pydantic model for updating workspace API key."""

    new_api_key: str
    workspace_name: str

    model_config = ConfigDict(from_attributes=True)


class WorkspaceRetrieve(BaseModel):
    """Pydantic model for workspace retrieval."""

    api_daily_quota: Optional[int] = None
    api_key_first_characters: Optional[str] = None
    api_key_updated_datetime_utc: Optional[datetime] = None
    content_quota: Optional[int] = None
    created_datetime_utc: datetime
    updated_datetime_utc: Optional[datetime] = None
    workspace_id: int
    workspace_name: str

    model_config = ConfigDict(from_attributes=True)


class WorkspaceSwitch(BaseModel):
    """Pydantic model for switching workspaces.

    NB: Switching workspaces should NOT require the user's password since this
    functionality is only available after a user authenticates with their username and
    password.
    """

    workspace_name: str

    model_config = ConfigDict(from_attributes=True)


class WorkspaceUpdate(BaseModel):
    """Pydantic model for workspace updates."""

    api_daily_quota: int | None = DEFAULT_API_QUOTA
    content_quota: int | None = DEFAULT_CONTENT_QUOTA
    workspace_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
