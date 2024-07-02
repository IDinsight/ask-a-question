from pydantic import BaseModel


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


class DashboardOverview(BaseModel):
    """
    This class is used to define the schema for the dashboard overview
    """

    stats_cards: StatsCards
