"""This module contains the Pydantic models for user tools endpoints."""

from pydantic import BaseModel, ConfigDict


class KeyResponse(BaseModel):
    """Pydantic model for key response."""

    new_api_key: str
    username: str

    model_config = ConfigDict(from_attributes=True)


class RequireRegisterResponse(BaseModel):
    """Pydantic model for require registration response."""

    require_register: bool

    model_config = ConfigDict(from_attributes=True)
