"""This module contains the Pydantic models for user tools endpoints."""

from pydantic import BaseModel, ConfigDict


class RequireRegisterResponse(BaseModel):
    """Pydantic model for require registration response."""

    require_register: bool

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
