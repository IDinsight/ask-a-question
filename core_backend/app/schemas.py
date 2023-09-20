from pydantic import BaseModel
from datetime import datetime


class UserQueryBase(BaseModel):
    """
    Pydantic model for query APIs
    """

    query_text: str
    query_metadata: dict = {}


class UserQueryCreate(UserQueryBase):
    """
    Complete User schema.
    """

    query_datetime_utc: datetime
    feedback_secret_key: str

    class Config:
        """allow attribute access"""

        from_attribute = True


class UserQueryResponse(BaseModel):
    """
    Pydantic model for response to Query
    """

    query_id: int
    response_text: int
    score: float
    debug_info: dict = {}


class FeedbackBase(BaseModel):
    """
    Pydantic model for feedback
    """

    query_id: int
    feedback_text: str
    feedback_secret_key: str

    class Config:
        """allow attribute access"""

        from_attribute = True
