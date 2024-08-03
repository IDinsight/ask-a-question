from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..llm_call.llm_prompts import IdentifiedLanguage
from ..schemas import FeedbackSentiment, QuerySearchResult


class QueryBase(BaseModel):
    """
    Question answering query base class.
    """

    query_text: str = Field(..., examples=["What is AAQ?"])
    session_id: Optional[int] = None
    generate_llm_response: bool = Field(False)
    query_metadata: dict = Field({}, examples=[{"some_key": "some_value"}])

    model_config = ConfigDict(from_attributes=True)


class QueryRefined(QueryBase):
    """
    Question answering query class with additional data
    """

    user_id: int
    query_text_original: str
    original_language: IdentifiedLanguage | None = None


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
    UNABLE_TO_GENERATE_RESPONSE = "unable_to_generate_response"
    ALIGNMENT_TOO_LOW = "alignment_too_low"


class QueryResponse(BaseModel):
    """
    Pydantic model for response to Query
    """

    query_id: int = Field(..., examples=[1])
    session_id: Optional[int] = None
    feedback_secret_key: str = Field(..., examples=["secret-key-12345-abcde"])
    llm_response: str | None = Field(None, examples=["Example LLM response"])
    search_results: Dict[int, QuerySearchResult] | None = Field(
        None,
        examples=[
            {
                "query_id": 1,
                "session_id": 1,
                "feedback_secret_key": "secret-key-12345-abcde",
                "llm_response": "Example LLM response "
                "(null if generate_llm_response is false)",
                "search_results": {
                    "0": {
                        "title": "Example content title",
                        "text": "Example content text",
                        "id": 23,
                        "distance": 0.1,
                    },
                    "1": {
                        "title": "Another example content title",
                        "text": "Another example content text",
                        "id": 12,
                        "distance": 0.2,
                    },
                },
                "debug_info": {"example": "debug-info"},
            }
        ],
    )
    debug_info: dict = Field({}, examples=[{"example": "debug-info"}])

    model_config = ConfigDict(from_attributes=True)


class QueryResponseError(QueryResponse):
    """
    Pydantic model when there is an error. Inherits from QueryResponse.
    """

    error_type: ErrorType = Field(..., examples=["example_error"])
    error_message: Optional[str] = Field(None, examples=["Example error message"])

    model_config = ConfigDict(from_attributes=True)


class ResponseFeedbackBase(BaseModel):
    """
    Response feedback base class.
    Feedback secret key must be retrieved from query response.
    """

    query_id: int = Field(..., examples=[1])
    session_id: Optional[int] = None
    feedback_sentiment: FeedbackSentiment = Field(
        FeedbackSentiment.UNKNOWN, examples=["positive"]
    )
    feedback_text: Optional[str] = Field(None, examples=["This is helpful"])
    feedback_secret_key: str = Field(..., examples=["secret-key-12345-abcde"])

    model_config = ConfigDict(from_attributes=True)


class ContentFeedback(ResponseFeedbackBase):
    """
    Content-level feedback class.
    Feedback secret key must be retrieved from query response.
    """

    content_id: int = Field(..., examples=[1])

    model_config = ConfigDict(from_attributes=True)
