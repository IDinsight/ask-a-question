from enum import Enum
from typing import Dict

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema

from ..llm_call.llm_prompts import IdentifiedLanguage
from ..schemas import FeedbackSentiment, QuerySearchResult


class QueryBase(BaseModel):
    """
    Question answering query base class.
    """

    query_text: str = Field(..., examples=["What is AAQ?"])
    generate_llm_response: bool = Field(False)
    query_metadata: dict = Field({}, examples=[{"some_key": "some_value"}])
    session_id: SkipJsonSchema[int | None] = Field(default=None, exclude=True)

    model_config = ConfigDict(from_attributes=True)


class QueryRefined(QueryBase):
    """
    Question answering query class with additional data
    """

    user_id: int
    query_text_original: str
    generate_tts: bool = Field(False)
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
    TTS_ERROR = "tts_error"
    STT_ERROR = "stt_error"


class QueryResponse(BaseModel):
    """
    Pydantic model for response to Query
    """

    query_id: int = Field(..., examples=[1])
    session_id: int | None = Field(None, exclude=True)
    feedback_secret_key: str = Field(..., examples=["secret-key-12345-abcde"])
    llm_response: str | None = Field(None, examples=["Example LLM response"])

    search_results: Dict[int, QuerySearchResult] | None = Field(
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
    debug_info: dict = Field({}, examples=[{"example": "debug-info"}])

    model_config = ConfigDict(from_attributes=True)


class QueryAudioResponse(QueryResponse):
    """
    Pydantic model for response to a Voice Query with audio response and Text response
    """

    tts_filepath: str | None = Field(
        None,
        examples=[
            "https://storage.googleapis.com/this-is-an-example/stt-voice-notes/uuidv4().hex.mp3"
        ],
    )
    model_config = ConfigDict(from_attributes=True)


class QueryResponseError(QueryResponse):
    """
    Pydantic model when there is an error. Inherits from QueryResponse.
    """

    error_type: ErrorType = Field(..., examples=["example_error"])
    error_message: str | None = Field(None, examples=["Example error message"])

    model_config = ConfigDict(from_attributes=True)


class ResponseFeedbackBase(BaseModel):
    """
    Response feedback base class.
    Feedback secret key must be retrieved from query response.
    """

    query_id: int = Field(..., examples=[1])
    session_id: SkipJsonSchema[int | None] = None
    feedback_sentiment: FeedbackSentiment = Field(
        FeedbackSentiment.UNKNOWN, examples=["positive"]
    )
    feedback_text: str | None = Field(None, examples=["This is helpful"])
    feedback_secret_key: str = Field(..., examples=["secret-key-12345-abcde"])

    model_config = ConfigDict(from_attributes=True)


class ContentFeedback(ResponseFeedbackBase):
    """
    Content-level feedback class.
    Feedback secret key must be retrieved from query response.
    """

    content_id: int = Field(..., examples=[1])

    model_config = ConfigDict(from_attributes=True)
