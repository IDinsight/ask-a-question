"""This module contains tests for the dashboard performance endpoint."""

from datetime import datetime, timezone
from typing import AsyncGenerator

import numpy as np
import pytest
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import delete

from core_backend.app.dashboard.models import get_content_details
from core_backend.app.dashboard.routers import (
    DashboardTimeFilter,
    get_freq_start_end_date,
    retrieve_performance,
)
from core_backend.app.question_answer.models import (
    ContentFeedbackDB,
    QueryDB,
    QueryResponseContentDB,
    save_content_feedback_to_db,
    save_content_for_query_to_db,
    save_user_query_to_db,
)
from core_backend.app.question_answer.schemas import (
    ContentFeedback,
    QueryBase,
    QuerySearchResult,
)
from core_backend.app.schemas import FeedbackSentiment

from .conftest import MockDatetime

N_CONTENT_SHARED = [12, 10, 8, 6, 4]


def get_halfway_delta(*, frequency: str) -> relativedelta:
    """Get the halfway delta for the given frequency.

    Parameters
    ----------
    frequency
        The frequency to get the halfway delta for.

    Returns
    -------
    relativedelta
        The halfway delta for the given frequency.

    Raises
    -------
    ValueError
        If the frequency is not valid.
    """

    if frequency == "year":
        delta = relativedelta(days=180)
    elif frequency == "month":
        delta = relativedelta(days=15)
    elif frequency == "week":
        delta = relativedelta(days=4)
    elif frequency == "day":
        delta = relativedelta(hours=12)
    else:
        raise ValueError("Invalid request parameter")

    return delta


@pytest.fixture(params=["year", "month", "week", "day"])
async def content_with_query_history(
    request: pytest.FixtureRequest,
    faq_contents_in_workspace_1: list[int],
    asession: AsyncSession,
    workspace_1_id: int,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[str, None]:
    """This fixture creates a set of query content records in workspace 1. The length
    of `N_CONTENT_SHARED` is the number of contents that will have a share history
    created. `N_CONTENT_SHARED` shows how many it will create for the current period
    for each content. The previous period will be ~1/2 of the current period and the
    period before that will be ~1/3 of the current period.

    Parameters
    ----------
    request
        The request object.
    faq_contents_in_workspace_1
        The list of FAQ contents in workspace 1.
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_1_id
        The ID of workspace 1.
    monkeypatch
        The monkeypatch fixture.

    Yields
    ------
    str
        The frequency of the query history.
    """

    delta = get_halfway_delta(frequency=request.param)

    # We reuse this one query ID for creating multiple search results. This is just a
    # convenience but would not happen in the actual application.
    query = QueryBase(
        generate_llm_response=False,
        query_metadata={},
        query_text="Test query - content history",
    )
    query_db = await save_user_query_to_db(
        asession=asession, user_query=query, workspace_id=workspace_1_id
    )
    content_ids = faq_contents_in_workspace_1[: len(N_CONTENT_SHARED)]

    for idx, (n_response, content_id) in enumerate(zip(N_CONTENT_SHARED, content_ids)):
        query_search_results = {}
        time_of_record = datetime.now(timezone.utc) - delta
        monkeypatch.setattr(
            "core_backend.app.question_answer.models.datetime",
            MockDatetime(date=time_of_record),
        )
        for i in range(n_response):
            query_search_results.update(
                {
                    idx * 100
                    + i: QuerySearchResult(
                        distance=0.5,
                        id=content_id,
                        text="test text",
                        title=f"test current period title {content_id}",
                    )
                }
            )
        await save_content_for_query_to_db(
            asession=asession,
            contents=query_search_results,
            query_id=query_db.query_id,
            session_id=1,
            workspace_id=workspace_1_id,
        )

        if idx % 2 == 0:
            sentiment = FeedbackSentiment.POSITIVE
        else:
            sentiment = FeedbackSentiment.NEGATIVE

        content_feedback = ContentFeedback(
            content_id=faq_contents_in_workspace_1[0],
            feedback_secret_key="secret key",
            feedback_sentiment=sentiment,
            feedback_text="Great content",
            query_id=query_db.query_id,
            session_id=query_db.session_id,
        )

        await save_content_feedback_to_db(asession=asession, feedback=content_feedback)

        query_search_results = {}
        time_of_record = datetime.now(timezone.utc) - delta - delta - delta
        monkeypatch.setattr(
            "core_backend.app.question_answer.models.datetime",
            MockDatetime(date=time_of_record),
        )
        for i in range(n_response // 2):
            query_search_results.update(
                {
                    idx * 100
                    + i
                    + n_response: QuerySearchResult(
                        distance=0.5,
                        id=content_id,
                        text="test text",
                        title="test previous period title",
                    )
                }
            )
        await save_content_for_query_to_db(
            asession=asession,
            contents=query_search_results,
            query_id=query_db.query_id,
            session_id=1,
            workspace_id=workspace_1_id,
        )

        content_feedback = ContentFeedback(
            content_id=faq_contents_in_workspace_1[0],
            feedback_secret_key="secret key",
            feedback_sentiment=sentiment,
            feedback_text="Great content",
            query_id=query_db.query_id,
            session_id=query_db.session_id,
        )

        await save_content_feedback_to_db(asession=asession, feedback=content_feedback)

        query_search_results = {}
        time_of_record = (
            datetime.now(timezone.utc) - delta - delta - delta - delta - delta
        )
        monkeypatch.setattr(
            "core_backend.app.question_answer.models.datetime",
            MockDatetime(date=time_of_record),
        )
        for i in range(n_response // 3):
            query_search_results.update(
                {
                    idx * 100
                    + i
                    + 2
                    * n_response: QuerySearchResult(
                        distance=0.5,
                        id=content_id,
                        text="test text",
                        title="test previous x2 period title",
                    )
                }
            )
        await save_content_for_query_to_db(
            asession=asession,
            contents=query_search_results,
            query_id=query_db.query_id,
            session_id=1,
            workspace_id=workspace_1_id,
        )

        content_feedback = ContentFeedback(
            content_id=faq_contents_in_workspace_1[0],
            feedback_secret_key="secret key",
            feedback_sentiment=sentiment,
            feedback_text="Great content",
            query_id=query_db.query_id,
            session_id=query_db.session_id,
        )

        await save_content_feedback_to_db(asession=asession, feedback=content_feedback)

    yield request.param

    delete_content_history = delete(QueryResponseContentDB).where(
        QueryResponseContentDB.query_id == query_db.query_id
    )
    await asession.execute(delete_content_history)
    delete_feedback = delete(ContentFeedbackDB).where(
        ContentFeedbackDB.query_id == query_db.query_id
    )
    await asession.execute(delete_feedback)
    delete_query = delete(QueryDB).where(QueryDB.query_id == query_db.query_id)
    await asession.execute(delete_query)
    await asession.commit()


@pytest.mark.parametrize("n_top", [1, 3, 10, 500])
async def test_dashboard_performance(
    n_top: int,
    content_with_query_history: DashboardTimeFilter,
    asession: AsyncSession,
    workspace_1_id: int,
) -> None:
    """Test the dashboard performance endpoint.

    Parameters
    ----------
    n_top
        The number of top contents to retrieve.
    content_with_query_history
        The content with query history.
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_1_id
        The ID of workspace 1.
    """

    frequency, start_date, end_date = get_freq_start_end_date(
        timeframe=content_with_query_history
    )
    performance_stats = await retrieve_performance(
        asession=asession,
        end_date=end_date,
        frequency=frequency,
        start_date=start_date,
        top_n=n_top,
        workspace_id=workspace_1_id,
    )
    time_series = performance_stats.content_time_series
    n_content_expected = min(n_top, len(N_CONTENT_SHARED))
    assert len(time_series) == n_content_expected
    for content_count, content_stats in zip(N_CONTENT_SHARED, time_series):
        assert (
            sum(list(content_stats.query_count_time_series.values())) == content_count
        )


async def test_cannot_access_other_user_stats(
    content_with_query_history: DashboardTimeFilter,
    asession: AsyncSession,
    workspace_2_id: int,
) -> None:
    """Test that a user cannot access another user's stats.

    Parameters
    ----------
    content_with_query_history
        The content with query history.
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_2_id
        The ID of workspace 2.
    """

    frequency, start_date, end_date = get_freq_start_end_date(
        timeframe=content_with_query_history
    )

    performance_stats = await retrieve_performance(
        asession=asession,
        end_date=end_date,
        frequency=frequency,
        start_date=start_date,
        top_n=1,
        workspace_id=workspace_2_id,
    )

    time_series = performance_stats.content_time_series
    assert len(time_series) == 0


async def test_drawer_data(
    content_with_query_history: DashboardTimeFilter,
    asession: AsyncSession,
    faq_contents_in_workspace_1: list[int],
    workspace_1_id: int,
) -> None:
    """Test the drawer data endpoint.

    Parameters
    ----------
    content_with_query_history
        The content with query history.
    asession
        The SQLAlchemy async session to use for all database connections.
    faq_contents_in_workspace_1
        The list of FAQ contents in workspace 1.
    workspace_1_id
        The ID of workspace 1.
    """

    frequency, start_date, end_date = get_freq_start_end_date(
        timeframe=content_with_query_history
    )
    max_feedback_records = 10

    drawer_data = await get_content_details(
        asession=asession,
        content_id=faq_contents_in_workspace_1[0],
        end_date=end_date,
        frequency=frequency,
        max_feedback_records=10,
        start_date=start_date,
        workspace_id=workspace_1_id,
    )

    assert drawer_data.query_count == N_CONTENT_SHARED[0]
    assert drawer_data.positive_votes == np.ceil(len(N_CONTENT_SHARED) / 2)
    assert len(drawer_data.user_feedback) == min(
        len(N_CONTENT_SHARED), max_feedback_records
    )
    assert drawer_data.negative_votes == np.floor(len(N_CONTENT_SHARED) / 2)
