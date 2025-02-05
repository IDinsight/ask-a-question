"""This module contains Pydantic models for dashboard endpoints."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, Field
from pydantic.functional_validators import AfterValidator


def has_all_days(d: dict[str, int]) -> dict[str, int]:
    """This function is used to validate that all days are present in the data.

    Parameters
    ----------
    d
        Dictionary whose keys are valid `Day` strings and whose values are counts.

    Returns
    -------
    dict[str, int]
        The validated dictionary.
    """

    assert set(d.keys()) - set(get_args(Day)) == set(), "Missing some days in data"
    return d


Day = Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DayCount = Annotated[dict[Day, int], AfterValidator(has_all_days)]
TimeHours = Literal[
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


class AIFeedbackSummary(BaseModel):
    """Pydantic model for AI feedback summary."""

    ai_summary: str | None


class BokehContentItem(BaseModel):
    """Pydantic model for Bokeh content item."""

    content_id: int
    content_text: str
    content_title: str


class ContentFeedbackStats(BaseModel):
    """Pydantic model for content feedback stats."""

    n_negative: int
    n_positive: int
    percentage_negative_increase: float
    percentage_positive_increase: float


class Heatmap(BaseModel):
    """Pydantic model for heatmap."""

    h00_00: DayCount = Field(..., alias="00:00")
    h02_00: DayCount = Field(..., alias="02:00")
    h04_00: DayCount = Field(..., alias="04:00")
    h06_00: DayCount = Field(..., alias="06:00")
    h08_00: DayCount = Field(..., alias="08:00")
    h10_00: DayCount = Field(..., alias="10:00")
    h12_00: DayCount = Field(..., alias="12:00")
    h14_00: DayCount = Field(..., alias="14:00")
    h16_00: DayCount = Field(..., alias="16:00")
    h18_00: DayCount = Field(..., alias="18:00")
    h20_00: DayCount = Field(..., alias="20:00")
    h22_00: DayCount = Field(..., alias="22:00")


class OverviewTimeSeries(BaseModel):
    """Pydantic model for line chart."""

    downvoted: dict[str, int]
    normal: dict[str, int]
    urgent: dict[str, int]


class ResponseFeedbackStats(BaseModel):
    """Pydantic model for response feedback stats."""

    n_negative: int
    n_positive: int
    percentage_negative_increase: float
    percentage_positive_increase: float


class TimeFrequency(str, Enum):
    """Enumeration for time frequency."""

    Day = "Day"
    Hour = "Hour"
    Month = "Month"
    Week = "Week"


class QueryStats(BaseModel):
    """Pydantic model for query stats."""

    n_questions: int
    percentage_increase: float


class Topic(BaseModel):
    """Pydantic model for one topic extracted from the user queries. Used for insights
    page.
    """

    topic_id: int
    topic_name: str
    topic_popularity: int
    topic_samples: list[dict[str, str]]
    topic_summary: str


class TopContentBase(BaseModel):
    """Pydantic model for top content base."""

    title: str


class TopicsData(BaseModel):
    """Pydantic model for a large group of individual topics. Used for insights page."""

    data: list[Topic]
    error_message: str | None = None
    failure_step: str | None = None
    refreshTimeStamp: str
    status: Literal["not_started", "in_progress", "completed", "error"]


class UrgencyStats(BaseModel):
    """Pydantic model for urgency stats."""

    n_urgent: int
    percentage_increase: float


class UserFeedback(BaseModel):
    """Pydantic model for user feedback."""

    feedback: str
    question: str
    timestamp: datetime


class UserQuery(BaseModel):
    """Pydantic model for insights for user queries."""

    query_datetime_utc: datetime
    query_id: int
    query_text: str


class DetailsDrawer(BaseModel):
    """Pydantic model for details drawer."""

    daily_query_count_avg: int
    negative_votes: int
    positive_votes: int
    query_count: int
    time_series: dict[str, dict[str, int]]
    title: str
    user_feedback: list[UserFeedback]


class StatsCards(BaseModel):
    """Pydantic model for stats cards."""

    content_feedback_stats: ContentFeedbackStats
    query_stats: QueryStats
    response_feedback_stats: ResponseFeedbackStats
    urgency_stats: UrgencyStats


class TopContent(TopContentBase):
    """Pydantic model for top content."""

    last_updated: datetime
    negative_votes: int
    positive_votes: int
    query_count: int


class DashboardOverview(BaseModel):
    """Pydantic model for dashboard overview."""

    heatmap: Heatmap
    stats_cards: StatsCards
    time_series: OverviewTimeSeries
    top_content: list[TopContent]


class TopContentTimeSeries(TopContentBase):
    """Pydantic model for top content time series."""

    id: int
    negative_votes: int
    positive_votes: int
    query_count_time_series: dict[str, int]
    total_query_count: int


class DashboardPerformance(BaseModel):
    """Pydantic model for dashboard performance."""

    content_time_series: list[TopContentTimeSeries]
