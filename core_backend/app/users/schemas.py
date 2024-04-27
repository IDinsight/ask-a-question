from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    """
    Pydantic model for user creation
    """

    username: str
    user_id: str
    retrieval_key: str
    created_datetime_utc: datetime
    updated_datetime_utc: datetime

    model_config = ConfigDict(from_attributes=True)
