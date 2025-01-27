"""This module contains Pydantic models for workspaces."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class WorkspaceCreate(BaseModel):
    """Pydantic model for workspace creation."""

    api_daily_quota: Optional[int] = None
    content_quota: Optional[int] = None
    workspace_name: str

    model_config = ConfigDict(from_attributes=True)


class WorkspaceKeyResponse(BaseModel):
    """Pydantic model for updating workspace API key."""

    new_api_key: str
    workspace_name: str

    model_config = ConfigDict(from_attributes=True)


class WorkspaceQuotaResponse(BaseModel):
    """Pydantic model for updating workspace quotas."""

    new_api_daily_quota: int
    new_content_quota: int
    workspace_name: str

    model_config = ConfigDict(from_attributes=True)


class WorkspaceRetrieve(BaseModel):
    """Pydantic model for workspace retrieval."""

    api_daily_quota: Optional[int] = None
    api_key_first_characters: str
    api_key_updated_datetime_utc: datetime
    content_quota: Optional[int] = None
    created_datetime_utc: datetime
    updated_datetime_utc: datetime
    workspace_id: int
    workspace_name: str

    model_config = ConfigDict(from_attributes=True)


class WorkspaceUpdate(BaseModel):
    """Pydantic model for workspace updates."""

    api_daily_quota: Optional[int] = None
    content_quota: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
