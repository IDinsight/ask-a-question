"""This module contains Pydantic models for user tools endpoints."""

from pydantic import BaseModel, ConfigDict


class RequireRegisterResponse(BaseModel):
    """Pydantic model for require registration response."""

    require_register: bool

    model_config = ConfigDict(from_attributes=True)
