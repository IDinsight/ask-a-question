from enum import Enum

from pydantic import BaseModel, ConfigDict


class FeedbackSentiment(str, Enum):
    """
    Enum for feedback sentiment
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"


class QuerySearchResult(BaseModel):
    """
    Pydantic model for each individual search result
    """

    retrieved_title: str
    retrieved_text: str
    retrieved_content_id: int
    distance: float

    model_config = ConfigDict(from_attributes=True)
