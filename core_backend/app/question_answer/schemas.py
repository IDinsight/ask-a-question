from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict

from ..llm_call.llm_prompts import IdentifiedLanguage
from ..schemas import FeedbackSentiment, QuerySearchResult


class QueryBase(BaseModel):
    """
    Question answering query base class.
    """

    query_text: str
    query_metadata: dict = {}

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "query_text": "What is AAQ?",
                    "query_metadata": {"source": "optinal-metadata-example"},
                },
            ]
        },
    )


class QueryRefined(QueryBase):
    """
    Question answering query class with additional data
    """

    query_text_original: str
    original_language: IdentifiedLanguage | None = None


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

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "query_id": 1,
                    "content_response": {
                        "0": {
                            "retrieved_title": "Example content title",
                            "retrieved_text": "Example content text",
                            "retrieved_content_id": 23,
                            "distance": 0.1,
                        },
                        "1": {
                            "retrieved_title": "Another example content title",
                            "retrieved_text": "Another example content text",
                            "retrieved_content_id": 12,
                            "distance": 0.2,
                        },
                    },
                    "llm_response": "Example LLM response"
                    "(not applicable for /embeddings-search)",
                    "feedback_secret_key": "secret-key-12345-abcde",
                    "debug_info": {"example": "debug-info"},
                    "state": "final",
                }
            ]
        },
    )


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
    Response feedback base class.
    Feedback secret key must be retrieved from query response.
    """

    query_id: int
    feedback_sentiment: FeedbackSentiment = FeedbackSentiment.UNKNOWN
    feedback_text: Optional[str] = None
    feedback_secret_key: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "query_id": 1,
                    "feedback_sentiment": "negative",
                    "feedback_text": "Not helpful",
                    "feedback_secret_key": "secret-key-12345-abcde",
                }
            ]
        },
    )


class ContentFeedback(ResponseFeedbackBase):
    """
    Content-level feedback class.
    Feedback secret key must be retrieved from query response.
    """

    content_id: int

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "content_id": 1,
                    "query_id": 1,
                    "feedback_sentiment": "positive",
                    "feedback_text": "This content is very helpful",
                    "feedback_secret_key": "secret-key-12345-abcde",
                }
            ]
        },
    )
