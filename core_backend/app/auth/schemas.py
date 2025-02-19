"""This module contains Pydantic models for user authentication and Google login
data.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from ..users.schemas import UserRoles

AccessLevel = Literal["fullaccess"]
TokenType = Literal["bearer"]


class AuthenticatedUser(BaseModel):
    """Pydantic model for authenticated user.

    NB: A user is authenticated within a workspace.
    """

    access_level: AccessLevel
    user_role: UserRoles
    username: str
    workspace_name: str
    model_config = ConfigDict(from_attributes=True)


class AuthenticationDetails(BaseModel):
    """Pydantic model for authentication details."""

    access_level: AccessLevel
    access_token: str
    token_type: TokenType
    user_role: UserRoles
    username: str
    workspace_name: str

    model_config = ConfigDict(from_attributes=True)


class GoogleLoginData(BaseModel):
    """Pydantic model for Google login data."""

    client_id: str
    credential: str

    model_config = ConfigDict(from_attributes=True)
