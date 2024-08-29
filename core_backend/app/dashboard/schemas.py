from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, Field
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

Day = Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class TimeFrequency(str, Enum):
    """
    This class is used to define the schema for the time frequency
    """

    Day = "Day"
    Week = "Week"
    Hour = "Hour"


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


DayCount = Annotated[dict[Day, int], AfterValidator(has_all_days)]


class Heatmap(BaseModel):
    """
    This class is used to define the schema for the heatmap
    """

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
    """
    This class is used to define the schema for the line chart
    """

    urgent: dict[str, int]
    not_urgent_escalated: dict[str, int]
    not_urgent_not_escalated: dict[str, int]


class TopContentBase(BaseModel):
    """
    This class is used to define the schema for the top content basic
    """

    title: str


class TopContent(TopContentBase):
    """
    This class is used to define the schema for the top content
    """

    query_count: int
    positive_votes: int
    negative_votes: int
    last_updated: datetime


class TopContentTimeSeries(TopContentBase):
    """
    This class is used to define the schema for the top content time series
    """

    id: int
    query_count_time_series: dict[str, int]
    positive_votes: int
    negative_votes: int
    total_query_count: int


class DashboardOverview(BaseModel):
    """
    This class is used to define the schema for the dashboard overview
    """

    stats_cards: StatsCards
    heatmap: Heatmap
    time_series: OverviewTimeSeries
    top_content: list[TopContent]


class Topic(BaseModel):
    """
    This class is used to define the schema for one topic
    extracted from the user queries. Used for Insights page.
    """

    topic_id: int
    topic_samples: list[dict[str, str]]
    topic_name: str
    topic_summary: str
    topic_popularity: int


class TopicsData(BaseModel):
    """
    This class is used to define the schema for the a large group
    of individual Topics. Used for Insights page.
    """

    refreshTimeStamp: str
    data: list[Topic]
    unclustered_queries: list[dict[str, str]]


class UserQuery(BaseModel):
    """
    This class is used to define the schema for the insights queries
    """

    query_id: int
    query_text: str
    query_datetime_utc: datetime


class QueryCollection(BaseModel):
    """
    This class is used to define the schema for the insights queries data
    """

    n_queries: int
    queries: list[UserQuery]


class UserFeedback(BaseModel):
    """
    This class is used to define the schema for the user feedback
    """

    timestamp: datetime
    question: str
    feedback: str


class DetailsDrawer(BaseModel):
    """
    This class is used to define the schema for the details drawer
    """

    title: str
    query_count: int
    positive_votes: int
    negative_votes: int
    daily_query_count_avg: int
    time_series: dict[str, dict[str, int]]
    user_feedback: list[UserFeedback]


class DashboardPerformance(BaseModel):
    """
    This class is used to define the schema for the dashboard performance page
    """

    content_time_series: list[TopContentTimeSeries]


class AIFeedbackSummary(BaseModel):
    """
    This class is used to define the schema for the AI feedback summary
    """

    ai_summary: str
