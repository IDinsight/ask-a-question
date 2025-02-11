"""This module contains Pydantic models for feedback and search results."""

from enum import Enum

from pydantic import BaseModel, ConfigDict


class FeedbackSentiment(str, Enum):
    """Enum for feedback sentiment."""

    NEGATIVE = "negative"
    POSITIVE = "positive"
    UNKNOWN = "unknown"


class QuerySearchResult(BaseModel):
    """Pydantic model for each individual search result."""

    distance: float
    id: int
    text: str
    title: str

    model_config = ConfigDict(from_attributes=True)
