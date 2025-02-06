"""This module contains Pydantic models for user authentication and Google login
data.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

AccessLevel = Literal["fullaccess"]
TokenType = Literal["bearer"]


class AuthenticatedUser(BaseModel):
    """Pydantic model for authenticated user.

    NB: A user is authenticated within a workspace.
    """

    access_level: AccessLevel
    username: str
    workspace_name: str

    model_config = ConfigDict(from_attributes=True)


class AuthenticationDetails(BaseModel):
    """Pydantic model for authentication details."""

    access_level: AccessLevel
    access_token: str
    token_type: TokenType
    username: str
    workspace_name: str

    # HACK FIX FOR FRONTEND: Need this to show User Management page for all users.
    is_admin: bool = True
    # HACK FIX FOR FRONTEND: Need this to show User Management page for all users.

    model_config = ConfigDict(from_attributes=True)


class GoogleLoginData(BaseModel):
    """Pydantic model for Google login data."""

    client_id: str
    credential: str

    model_config = ConfigDict(from_attributes=True)


class WorkspaceLogin(BaseModel):
    """Pydantic model for workspace login.

    NB: Logging into a workspace should NOT require the user's password since this
    functionality is only available after a user authenticates with their username and
    password.

    NB: If `workspace_name` is not provided, the user will be logged into their default
    workspace.
    """

    workspace_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
