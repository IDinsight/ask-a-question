from typing import Literal

from pydantic import BaseModel, ConfigDict

AccessLevel = Literal["fullaccess"]


class AuthenticatedUser(BaseModel):
    """
    Pydantic model for authenticated user
    """

    username: str
    access_level: AccessLevel

    model_config = ConfigDict(from_attributes=True)


class GoogleLoginData(BaseModel):
    """
    Pydantic model for Google login data
    """

    client_id: str
    credential: str

    model_config = ConfigDict(from_attributes=True)
