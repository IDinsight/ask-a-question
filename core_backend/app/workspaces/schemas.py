"""This module contains Pydantic models for workspaces."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class WorkspaceCreate(BaseModel):
    """Pydantic model for workspace creation."""

    api_daily_quota: int | None = -1
    content_quota: int | None = -1
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


class WorkspaceUpdate(BaseModel):
    """Pydantic model for workspace updates."""

    api_daily_quota: int | None = -1
    content_quota: int | None = -1
    workspace_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
