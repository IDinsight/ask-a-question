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

    title: str
    text: str
    id: int
    distance: float

    model_config = ConfigDict(from_attributes=True)
