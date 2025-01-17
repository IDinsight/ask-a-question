"""This module contains Pydantic models for user authentication and Google login
data.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

AccessLevel = Literal["fullaccess"]
TokenType = Literal["bearer"]


class AuthenticationDetails(BaseModel):
    """Pydantic model for authentication details."""

    access_level: AccessLevel
    access_token: str
    token_type: TokenType
    username: str
    is_admin: bool = True,  # Hack fix for frontend

    model_config = ConfigDict(from_attributes=True)


class AuthenticatedUser(BaseModel):
    """Pydantic model for authenticated user."""

    access_level: AccessLevel
    username: str

    model_config = ConfigDict(from_attributes=True)


class GoogleLoginData(BaseModel):
    """Pydantic model for Google login data."""

    client_id: str
    credential: str

    model_config = ConfigDict(from_attributes=True)
