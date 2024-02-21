from datetime import datetime
from enum import Enum
from typing import Annotated, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints, validator

from .configs.llm_prompts import IdentifiedLanguage

AccessLevel = Literal["fullaccess", "readonly"]


class UserQueryBase(BaseModel):
    """
    Pydantic model for query APIs
    """

    query_text: str
    query_metadata: dict = {}

    model_config = ConfigDict(from_attributes=True)


class ResultState(str, Enum):
    """
    Enum for Response state
    """

    FINAL = "final"
    IN_PROGRESS = "in_progress"
    ERROR = "error"


class ErrorType(str, Enum):
    """
    Enum for Error Type
    """

    QUERY_UNSAFE = "query_unsafe"
    UNKNOWN_LANGUAGE = "unknown_language"
    UNABLE_TO_TRANSLATE = "unable_to_translate"
    UNABLE_TO_PARAPHRASE = "unable_to_paraphrase"
    ALIGNMENT_TOO_LOW = "alignment_too_low"


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

    retrieved_title: str
    retrieved_text: str
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
    state: ResultState = ResultState.IN_PROGRESS

    model_config = ConfigDict(from_attributes=True)


class UserQueryResponseError(BaseModel):
    """
    Pydantic model when there is an error
    """

    query_id: int
    error_message: Optional[str] = None
    error_type: ErrorType
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

    # Ensure len("*{title}*\n\n{text}") <= 1600
    content_title: Annotated[str, StringConstraints(max_length=150)]
    content_text: Annotated[str, StringConstraints(max_length=1446)]
    content_language: str = "ENGLISH"
    content_metadata: dict = {}

    model_config = ConfigDict(from_attributes=True)

    @validator("content_language")
    def validate_language(cls, v: str) -> str:
        """
        Validator for language
        """

        if v not in IdentifiedLanguage.get_supported_languages():
            raise ValueError(f"Language {v} is not supported")

        return v


class ContentRetrieve(ContentCreate):
    """
    Pydantic model for content retrieval
    """

    content_id: int
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
