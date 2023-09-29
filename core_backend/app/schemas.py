from pydantic import BaseModel, ConfigDict, UUID4
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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class ContentCreate(BaseModel):
    """
    Pydantic model for content creation
    """

    content_metadata: dict = {}
    content_text: str

    model_config = ConfigDict(from_attributes=True)


class ContentRetrieve(ContentCreate):
    """
    Pydantic model for content retrieval
    """

    content_id: UUID4
    created_datetime_utc: datetime
    updated_datetime_utc: datetime


class ContentUpdate(ContentCreate):
    """
    Pydantic model for content edit
    """

    content_id: int


class ContentDelete(BaseModel):
    """
    Pydantic model for content deletiom
    """

    content_id: int
