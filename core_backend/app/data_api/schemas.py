"""This module contains Pydantic models for data API queries and responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContentFeedbackExtract(BaseModel):
    """Pydantic model for content feedback."""

    content_id: int
    feedback_datetime_utc: datetime
    feedback_id: int
    feedback_sentiment: str
    feedback_text: str | None

    model_config = ConfigDict(from_attributes=True)


class QueryResponseErrorExtract(BaseModel):
    """Pydantic model for when an error response is returned."""

    error_datetime_utc: datetime
    error_id: int
    error_message: str
    error_type: str

    model_config = ConfigDict(from_attributes=True)


class QueryResponseExtract(BaseModel):
    """Pydantic model for when a valid query response is returned."""

    llm_response: str | None
    response_datetime_utc: datetime
    response_id: int
    search_results: dict

    model_config = ConfigDict(from_attributes=True)


class ResponseFeedbackExtract(BaseModel):
    """Pydantic model for response feedback."""

    feedback_datetime_utc: datetime
    feedback_id: int
    feedback_sentiment: str
    feedback_text: str | None

    model_config = ConfigDict(from_attributes=True)


class QueryExtract(BaseModel):
    """Pydantic model for a query. Contains all related child models.

    NB: The model contains the workspace ID.
    """

    content_feedback: list[ContentFeedbackExtract]
    query_datetime_utc: datetime
    query_id: int
    query_metadata: dict
    query_text: str
    response: list[QueryResponseExtract]
    response_feedback: list[ResponseFeedbackExtract]
    workspace_id: int


class UrgencyQueryResponseExtract(BaseModel):
    """Pydantic model when valid response is returned."""

    details: dict
    is_urgent: bool
    matched_rules: list[str] | None
    response_datetime_utc: datetime
    urgency_response_id: int

    model_config = ConfigDict(from_attributes=True)


class UrgencyQueryExtract(BaseModel):
    """Pydantic model that is returned for an urgency query. Contains all related
    child models.

    NB: This model contains the workspace ID.
    """

    message_datetime_utc: datetime
    message_text: str
    response: UrgencyQueryResponseExtract | None
    urgency_query_id: int
    workspace_id: int
