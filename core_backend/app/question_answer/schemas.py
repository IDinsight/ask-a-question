from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict

from ..llm_call.llm_prompts import IdentifiedLanguage
from ..schemas import FeedbackSentiment


class QueryBase(BaseModel):
    """
    Pydantic model for query APIs
    """

    query_text: str
    query_metadata: dict = {}
    generate_tts: bool = False

    model_config = ConfigDict(from_attributes=True)


class QueryRefined(QueryBase):
    """
    Pydantic model for refined query
    """

    query_text_original: str
    original_language: IdentifiedLanguage | None = None


class QuerySearchResult(BaseModel):
    """
    Pydantic model for each individual search result
    """

    retrieved_title: str
    retrieved_text: str
    retrieved_content_id: int
    score: float

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
    OFF_TOPIC = "off_topic"
    UNINTELLIGIBLE_INPUT = "unintelligible_input"
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    UNABLE_TO_TRANSLATE = "unable_to_translate"
    UNABLE_TO_PARAPHRASE = "unable_to_paraphrase"
    ALIGNMENT_TOO_LOW = "alignment_too_low"
    TTS_ERROR = "tts_error"
    STT_ERROR = "stt_error"


class QueryResponse(BaseModel):
    """
    Pydantic model for response to Query
    """

    query_id: int
    content_response: Dict[int, QuerySearchResult] | None
    llm_response: Optional[str] = None
    feedback_secret_key: str
    debug_info: dict = {}
    state: ResultState = ResultState.IN_PROGRESS
    tts_file: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class QueryResponseError(BaseModel):
    """
    Pydantic model when there is an error
    """

    query_id: int
    error_message: Optional[str] = None
    error_type: ErrorType
    debug_info: dict = {}

    model_config = ConfigDict(from_attributes=True)


class ResponseFeedbackBase(BaseModel):
    """
    Pydantic model for feedback
    """

    query_id: int
    feedback_sentiment: FeedbackSentiment = FeedbackSentiment.UNKNOWN
    feedback_text: Optional[str] = None
    feedback_secret_key: str

    model_config = ConfigDict(from_attributes=True)


class ContentFeedback(ResponseFeedbackBase):
    """
    Pydantic model for content feedback
    """

    content_id: int

    model_config = ConfigDict(from_attributes=True)
