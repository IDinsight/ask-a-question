"""Pydantic schemas for the question-answer feature (incl. Turn.io payloads)."""

from __future__ import annotations

import textwrap
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema

from app.contents.schemas import QuerySearchResult


class FeedbackSentiment(str, Enum):
    """Enum for feedback sentiment."""

    NEGATIVE = "negative"
    POSITIVE = "positive"
    UNKNOWN = "unknown"



# ---- from core/languages
class IdentifiedLanguage(str, Enum):
    """Identified language of the user's input."""

    # AFRIKAANS = "AFRIKAANS"
    ENGLISH = "ENGLISH"
    FRENCH = "FRENCH"
    SPANISH = "SPANISH"
    HINDI = "HINDI"
    SWAHILI = "SWAHILI"
    UNINTELLIGIBLE = "UNINTELLIGIBLE"
    UNSUPPORTED = "UNSUPPORTED"
    # XHOSA = "XHOSA"
    # ZULU = "ZULU"

    @classmethod
    def get_supported_languages(cls) -> list[str]:
        """Return a list of supported languages.

        Returns
        -------
        list[str]
            A list of supported languages.
        """

        return [
            lang
            for lang in cls._member_names_
            if lang not in ("UNINTELLIGIBLE", "UNSUPPORTED")
        ]

    @classmethod
    def _missing_(cls, value: str) -> IdentifiedLanguage:  # type: ignore[override]
        """If language identified is not one of the supported language, it is
        classified as UNSUPPORTED.

        Parameters
        ----------
        value
            The language identified.

        Returns
        -------
        IdentifiedLanguage
            The identified language (i.e., UNSUPPORTED).
        """

        return cls.UNSUPPORTED

    @classmethod
    def get_prompt(cls) -> str:
        """Return the prompt for the language identification bot.

        Returns
        -------
        str
            The prompt for the language identification bot.
        """

        return textwrap.dedent(
            f"""
            You are a high-performing language identification bot that classifies the
            language of the user input into one of {", ".join(cls._member_names_)}.

            If the user input is
            1. in one of the supported languages, then respond with that language.
            2. written in a mix of languages, then respond with the dominant language.
            3. in a real language but not a supported language, then respond with
            UNSUPPORTED.
            4. unintelligible or gibberish, then respond with UNINTELLIGIBLE.

            Answer should be a single word and strictly one of
            [{", ".join(cls._member_names_)}]"""
        ).strip()


# ---- from question_answer/schemas
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

    chat_query_params: SkipJsonSchema[Optional[dict[str, Any]]] = Field(
        default=None, description="Query parameters for chat"
    )
    generate_llm_response: bool = Field(False)
    query_metadata: dict = Field(
        default_factory=dict, examples=[{"some_key": "some_value"}]
    )
    query_text: str = Field(..., examples=["What is AAQ?"])
    session_id: int | None = Field(default=None)
    turnio_api_key: Optional[str] = None
    wa_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class QueryRefined(QueryBase):
    """Pydantic model for question answering query with additional data.

    NB: This model contains the workspace ID.
    """

    generate_tts: bool = Field(False)
    original_language: IdentifiedLanguage | None = None
    query_text_original: str
    workspace_doc_language: str
    workspace_id: int


class QueryResponse(BaseModel):
    """Pydantic model for response to a question answering query."""

    debug_info: dict = Field(default_factory=dict, examples=[{"example": "debug-info"}])
    feedback_secret_key: str | None = Field(..., examples=["secret-key-12345-abcde"])
    llm_response: str | None = Field(None, examples=["Example LLM response"])
    message_type: Optional[str] = None
    query_id: int | None = Field(..., examples=[1])
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


# ---- from integrations/turnio/schemas
class TurnMessageBody(BaseModel):
    """
    Schema for the body of a text message using turn.io's API
    See: https://whatsapp.turn.io/docs/api/messages#text-messages
    """

    body: str

    model_config = ConfigDict(from_attributes=True)


class TurnMessage(BaseModel):
    """
    Schema for sending a message using turn.io's API.
    """

    preview_url: bool = False
    recipient_type: Literal["individual"] = "individual"
    to: str
    type: Literal["text", "audio", "image", "video", "interactive"] = "text"


class TurnTextMessage(TurnMessage):
    """
    Schema for sending a message using turn.io's API
    See: https://whatsapp.turn.io/docs/api/messages#text-messages
    """

    type: Literal["text"] = "text"
    text: TurnMessageBody


