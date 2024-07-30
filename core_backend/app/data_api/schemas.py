from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, ConfigDict


class QueryResponseExtract(BaseModel):
    """
    Model when valid response is returned
    """

    response_id: int
    search_results: Dict
    llm_response: str | None
    response_datetime_utc: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class QueryResponseErrorExtract(BaseModel):
    """
    Model when error response is returned
    """

    error_id: int
    error_message: str
    error_type: str
    error_datetime_utc: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class ResponseFeedbackExtract(BaseModel):
    """
    Model for feedback on response
    """

    feedback_id: int
    feedback_sentiment: str
    feedback_text: str | None
    feedback_datetime_utc: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class ContentFeedbackExtract(BaseModel):
    """
    Model for feedback on content
    """

    feedback_id: int
    feedback_sentiment: str
    feedback_text: str | None
    feedback_datetime_utc: datetime
    content_id: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class QueryExtract(BaseModel):
    """
    Main model that is returned for a query.
    Contains all related child models
    """

    query_id: int
    user_id: int
    query_text: str
    query_metadata: dict
    query_datetime_utc: datetime
    response: List[QueryResponseExtract]
    response_feedback: List[ResponseFeedbackExtract]
    content_feedback: List[ContentFeedbackExtract]


class UrgencyQueryResponseExtract(BaseModel):
    """
    Model when valid response is returned
    """

    urgency_response_id: int
    is_urgent: bool
    matched_rules: List[str] | None
    details: Dict
    response_datetime_utc: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class UrgencyQueryExtract(BaseModel):
    """
    Main model that is returned for an urgency query.
    Contains all related child models
    """

    urgency_query_id: int
    user_id: int
    message_text: str
    message_datetime_utc: datetime
    response: UrgencyQueryResponseExtract | None
