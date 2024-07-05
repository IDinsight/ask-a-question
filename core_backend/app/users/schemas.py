from typing import Optional

from pydantic import BaseModel, ConfigDict


# not yet used.
class UserCreate(BaseModel):
    """
    Pydantic model for user creation
    """

    username: str
    content_quota: int
    api_daily_quota: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreateWithPassword(UserCreate):
    """
    Pydantic model for user creation
    """

    password: str

    model_config = ConfigDict(from_attributes=True)
