from typing import Annotated, Dict, Literal, get_args

from pydantic import BaseModel
from pydantic.functional_validators import AfterValidator


class QueryStats(BaseModel):
    """
    This class is used to define the schema for the query stats
    """

    n_questions: int
    percentage_increase: float


class ResponseFeedbackStats(BaseModel):
    """
    This class is used to define the schema for the response feedback stats
    """

    n_positive: int
    n_negative: int
    percentage_positive_increase: float
    percentage_negative_increase: float


class ContentFeedbackStats(BaseModel):
    """
    This class is used to define the schema for the content feedback stats
    """

    n_positive: int
    n_negative: int
    percentage_positive_increase: float
    percentage_negative_increase: float


class UrgencyStats(BaseModel):
    """
    This class is used to define the schema for the urgency stats
    """

    n_urgent: int
    percentage_increase: float


class StatsCards(BaseModel):
    """
    This class is used to define the schema for the stats cards
    """

    query_stats: QueryStats
    response_feedback_stats: ResponseFeedbackStats
    content_feedback_stats: ContentFeedbackStats
    urgency_stats: UrgencyStats


Time = Literal[
    "00:00",
    "02:00",
    "04:00",
    "06:00",
    "08:00",
    "10:00",
    "12:00",
    "14:00",
    "16:00",
    "18:00",
    "20:00",
    "22:00",
]

Day = Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def has_all_keys(d: Dict[str, int]) -> Dict[str, int]:
    assert set(d.keys()) - set(get_args(Time)) == set(), "missing keys"
    return d


HourCount = Annotated[Dict[Time, int], AfterValidator(has_all_keys)]


class Heatmap(BaseModel):
    """
    This class is used to define the schema for the heatmap
    """

    Mon: HourCount
    Tue: HourCount
    Wed: HourCount
    Thu: HourCount
    Fri: HourCount
    Sat: HourCount
    Sun: HourCount


class DashboardOverview(BaseModel):
    """
    This class is used to define the schema for the dashboard overview
    """

    stats_cards: StatsCards
    heatmap: Heatmap
