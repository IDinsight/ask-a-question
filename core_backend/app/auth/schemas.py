from typing import Literal

from pydantic import BaseModel, ConfigDict

AccessLevel = Literal["fullaccess", "readonly"]


class AuthenticatedUser(BaseModel):
    """
    Pydantic model for authenticated user
    """

    username: str
    access_level: AccessLevel

    model_config = ConfigDict(from_attributes=True)
