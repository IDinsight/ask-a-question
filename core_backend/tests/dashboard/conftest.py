"""Fixtures shared by the dashboard tests."""

from typing import get_args

import pytest

from app.dashboard.schemas import DashboardOverview, TimeHours


@pytest.fixture
def empty_overview() -> DashboardOverview:
    """A valid `DashboardOverview` with every count set to zero.

    Router and service tests return it from faked service/repository calls, so it
    must pass the same validation FastAPI applies to the real response.

    Returns
    -------
    DashboardOverview
        An overview with an empty heatmap, zeroed stats and no top content.
    """

    feedback_stats = {
        "n_negative": 0,
        "n_positive": 0,
        "percentage_negative_increase": 0.0,
        "percentage_positive_increase": 0.0,
    }
    return DashboardOverview.model_validate(
        {
            # Every 2-hour bucket must be present; an empty day dict is valid.
            "heatmap": {hour: {} for hour in get_args(TimeHours)},
            "stats_cards": {
                "content_feedback_stats": feedback_stats,
                "query_stats": {"n_questions": 0, "percentage_increase": 0.0},
                "response_feedback_stats": feedback_stats,
                "urgency_stats": {"n_urgent": 0, "percentage_increase": 0.0},
            },
            "time_series": {"downvoted": {}, "normal": {}, "urgent": {}},
            "top_content": [],
        }
    )
