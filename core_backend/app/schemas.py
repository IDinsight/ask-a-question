from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import UUID4, BaseModel, ConfigDict

from .configs.llm_prompts import IdentifiedLanguage

AccessLevel = Literal["fullaccess", "readonly"]


class UserQueryBase(BaseModel):
    """
    Pydantic model for query APIs
    """

    query_text: str
    query_metadata: dict = {}

    model_config = ConfigDict(from_attributes=True)


class UserQueryRefined(UserQueryBase):
    """
    Pydantic model for refined query
    """

    query_text_original: str
    original_language: IdentifiedLanguage | None = None


class UserQuerySearchResult(BaseModel):
    """
    Pydantic model for each individual search result
    """

    response_text: str
    score: float

    model_config = ConfigDict(from_attributes=True)


class UserQueryResponse(BaseModel):
    """
    Pydantic model for response to Query
    """

    query_id: int
    content_response: Dict[int, UserQuerySearchResult] | None
    llm_response: Optional[str] = None
    feedback_secret_key: str
    debug_info: dict = {}

    model_config = ConfigDict(from_attributes=True)


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


class AuthenticatedUser(BaseModel):
    """
    Pydantic model for authenticated user
    """

    username: str
    access_level: AccessLevel

    model_config = ConfigDict(from_attributes=True)


class WhatsAppIncoming(BaseModel):
    """
    Pydantic model for Incoming WhatsApp message
    """

    phone_number: str
    message: str
    phone_id: str
    msg_id_from_whatsapp: str


class WhatsAppResponse(BaseModel):
    """
    Pydantic model for WhatsApp Response messages
    """

    incoming_id: int
    response_text: str
    response_datetime_utc: datetime
    response_status: int
