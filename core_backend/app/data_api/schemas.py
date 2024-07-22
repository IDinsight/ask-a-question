from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel


class QueryResponseModel(BaseModel):
    """
    Model when valid response is returned
    """

    response_id: int
    content_response: Dict
    llm_response: str | None
    response_datetime_utc: datetime


class QueryResponseErrorModel(BaseModel):
    """
    Model when error response is returned
    """

    error_id: int
    error_message: str
    error_type: str
    error_datetime_utc: datetime


class ResponseFeedbackModel(BaseModel):
    """
    Model for feedback on response
    """

    feedback_id: int
    feedback_sentiment: str
    feedback_text: str | None
    feedback_datetime_utc: datetime


class ContentFeedbackModel(BaseModel):
    """
    Model for feedback on content
    """

    feedback_id: int
    feedback_sentiment: str
    feedback_text: str | None
    feedback_datetime_utc: datetime
    content_id: int


class QueryModel(BaseModel):
    """
    Main model that is returned for a query.
    Contains all related child models
    """

    query_id: int
    user_id: int
    query_text: str
    query_metadata: dict
    query_datetime_utc: datetime
    response: QueryResponseModel | None
    response_error: QueryResponseErrorModel | None
    response_feedback: List[ResponseFeedbackModel]
    content_feedback: List[ContentFeedbackModel]
