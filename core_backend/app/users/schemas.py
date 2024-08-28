from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# not yet used.
class UserCreate(BaseModel):
    """
    Pydantic model for user creation
    """

    username: str
    content_quota: Optional[int] = None
    api_daily_quota: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreateWithPassword(UserCreate):
    """
    Pydantic model for user creation
    """

    password: str

    model_config = ConfigDict(from_attributes=True)


class UserRetrieve(BaseModel):
    """
    Pydantic model for user retrieval
    """

    user_id: int
    username: str
    content_quota: Optional[int]
    api_key_first_characters: Optional[str]
    api_key_updated_datetime_utc: Optional[datetime]
    created_datetime_utc: datetime
    updated_datetime_utc: datetime

    model_config = ConfigDict(from_attributes=True)
