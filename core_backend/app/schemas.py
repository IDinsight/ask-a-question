from enum import Enum


class FeedbackSentiment(str, Enum):
    """
    Enum for feedback sentiment
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
