"""This module contains Pydantic models for question answering queries and responses."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema

from ..llm_call.llm_prompts import IdentifiedLanguage
from ..schemas import FeedbackSentiment, QuerySearchResult


class ErrorType(str, Enum):
    """Enum for error types."""

    ALIGNMENT_TOO_LOW = "alignment_too_low"
    OFF_TOPIC = "off_topic"
    QUERY_UNSAFE = "query_unsafe"
    STT_ERROR = "stt_error"
    TTS_ERROR = "tts_error"
    UNABLE_TO_GENERATE_RESPONSE = "unable_to_generate_response"
    UNABLE_TO_PARAPHRASE = "unable_to_paraphrase"
    UNABLE_TO_TRANSLATE = "unable_to_translate"
    UNINTELLIGIBLE_INPUT = "unintelligible_input"
    UNSUPPORTED_LANGUAGE = "unsupported_language"


class QueryBase(BaseModel):
    """Pydantic model for question answering query."""

    chat_query_params: Optional[dict[str, Any]] = Field(
        default=None, description="Query parameters for chat"
    )
    generate_llm_response: bool = Field(False)
    query_metadata: dict = Field(
        default_factory=dict, examples=[{"some_key": "some_value"}]
    )
    query_text: str = Field(..., examples=["What is AAQ?"])
    session_id: SkipJsonSchema[int | None] = Field(default=None, exclude=True)

    model_config = ConfigDict(from_attributes=True)


class QueryRefined(QueryBase):
    """Pydantic model for question answering query with additional data.

    NB: This model contains the workspace ID.
    """

    generate_tts: bool = Field(False)
    original_language: IdentifiedLanguage | None = None
    query_text_original: str
    workspace_id: int


class QueryResponse(BaseModel):
    """Pydantic model for response to a question answering query."""

    debug_info: dict = Field(default_factory=dict, examples=[{"example": "debug-info"}])
    feedback_secret_key: str = Field(..., examples=["secret-key-12345-abcde"])
    llm_response: str | None = Field(None, examples=["Example LLM response"])
    message_type: Optional[str] = None
    query_id: int = Field(..., examples=[1])
    search_results: dict[int, QuerySearchResult] | None = Field(
        examples=[
            {
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
            }
        ],
    )
    session_id: int | None = Field(None, exclude=False)

    model_config = ConfigDict(from_attributes=True)


class QueryResponseError(QueryResponse):
    """Pydantic model when there is a query response error."""

    error_message: str | None = Field(None, examples=["Example error message"])
    error_type: ErrorType = Field(..., examples=["example_error"])

    model_config = ConfigDict(from_attributes=True)


class QueryAudioResponse(QueryResponse):
    """Pydantic model for response to a voice query with audio response and text
    response.
    """

    tts_filepath: str | None = Field(
        None,
        examples=[
            "https://storage.googleapis.com/example-bucket/random_uuid_filename.mp3"
        ],
    )

    model_config = ConfigDict(from_attributes=True)


class ResponseFeedbackBase(BaseModel):
    """Pydantic model for response feedback. Feedback secret key must be retrieved
    from query response.
    """

    feedback_secret_key: str = Field(..., examples=["secret-key-12345-abcde"])
    feedback_sentiment: FeedbackSentiment = Field(
        FeedbackSentiment.UNKNOWN, examples=["positive"]
    )
    feedback_text: str | None = Field(None, examples=["This is helpful"])
    query_id: int = Field(..., examples=[1])
    session_id: SkipJsonSchema[int | None] = None

    model_config = ConfigDict(from_attributes=True)


class ContentFeedback(ResponseFeedbackBase):
    """Pydantic model for content-level feedback. Feedback secret key must be
    retrieved from query response.
    """

    content_id: int = Field(..., examples=[1])

    model_config = ConfigDict(from_attributes=True)
