from datetime import datetime, timezone, tzinfo
from typing import AsyncGenerator, List, Optional

import numpy as np
import pytest
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import delete

from core_backend.app.dashboard.models import get_content_details
from core_backend.app.dashboard.routers import (
    DashboardTimeFilter,
    get_frequency_and_startdate,
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


class MockDatetime:
    def __init__(self, date: datetime):
        self.date = date

    def now(self, tz: Optional[tzinfo] = None) -> datetime:
        if tz is not None:
            return self.date.astimezone(tz)
        return self.date


def get_halfway_delta(frequency: str) -> relativedelta:
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


N_CONTENT_SHARED = [12, 10, 8, 6, 4]


@pytest.fixture(params=["year", "month", "week", "day"])
async def content_with_query_history(
    request: pytest.FixtureRequest,
    user: pytest.FixtureRequest,
    faq_contents: List[int],
    asession: AsyncSession,
    user1: int,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[str, None]:
    """
    This fixture creates a set of query content records. The length
    of N_CONTENT_SHARED is the number of contents that will have a share history
    created. N_CONTENT_SHARED shows how many it will create for the current
    period for each content. The previous period will be ~half of the current period
    and the period before that will be ~1/3 of the current period.
    """

    delta = get_halfway_delta(request.param)

    # We reuse this one query id for creating multiple search results
    # This is got convenience but would not happen in the actual application
    query = QueryBase(query_text="Test query - content history", query_metadata={})
    query_db = await save_user_query_to_db(
        user_id=user1,
        user_query=query,
        asession=asession,
    )

    content_ids = faq_contents[: len(N_CONTENT_SHARED)]
    for idx, (n_response, content_id) in enumerate(zip(N_CONTENT_SHARED, content_ids)):

        query_search_results = {}
        time_of_record = datetime.now(timezone.utc) - delta
        monkeypatch.setattr(
            "core_backend.app.question_answer.models.datetime",
            MockDatetime(time_of_record),
        )
        for i in range(n_response):
            query_search_results.update(
                {
                    idx * 100
                    + i: QuerySearchResult(
                        title=f"test current period title {content_id}",
                        text="test text",
                        id=content_id,
                        distance=0.5,
                    )
                }
            )
        await save_content_for_query_to_db(
            user1, 1, query_db.query_id, query_search_results, asession
        )

        if idx % 2 == 0:
            sentiment = FeedbackSentiment.POSITIVE
        else:
            sentiment = FeedbackSentiment.NEGATIVE

        content_feedback = ContentFeedback(
            query_id=query_db.query_id,
            session_id=query_db.session_id,
            feedback_sentiment=sentiment,
            feedback_text="Great content",
            feedback_secret_key="secret key",
            content_id=faq_contents[0],
        )

        await save_content_feedback_to_db(
            feedback=content_feedback,
            asession=asession,
        )

        query_search_results = {}
        time_of_record = datetime.now(timezone.utc) - delta - delta - delta
        monkeypatch.setattr(
            "core_backend.app.question_answer.models.datetime",
            MockDatetime(time_of_record),
        )
        for i in range(n_response // 2):
            query_search_results.update(
                {
                    idx * 100
                    + i
                    + n_response: QuerySearchResult(
                        title="test previous period title",
                        text="test text",
                        id=content_id,
                        distance=0.5,
                    )
                }
            )
        await save_content_for_query_to_db(
            user1, 1, query_db.query_id, query_search_results, asession
        )

        content_feedback = ContentFeedback(
            query_id=query_db.query_id,
            session_id=query_db.session_id,
            feedback_sentiment=sentiment,
            feedback_text="Great content",
            feedback_secret_key="secret key",
            content_id=faq_contents[0],
        )

        await save_content_feedback_to_db(
            feedback=content_feedback,
            asession=asession,
        )

        query_search_results = {}
        time_of_record = (
            datetime.now(timezone.utc) - delta - delta - delta - delta - delta
        )
        monkeypatch.setattr(
            "core_backend.app.question_answer.models.datetime",
            MockDatetime(time_of_record),
        )
        for i in range(n_response // 3):

            query_search_results.update(
                {
                    idx * 100
                    + i
                    + 2
                    * n_response: QuerySearchResult(
                        title="test previous x2 period title",
                        text="test text",
                        id=content_id,
                        distance=0.5,
                    )
                }
            )
        await save_content_for_query_to_db(
            user1, 1, query_db.query_id, query_search_results, asession
        )

        content_feedback = ContentFeedback(
            query_id=query_db.query_id,
            session_id=query_db.session_id,
            feedback_sentiment=sentiment,
            feedback_text="Great content",
            feedback_secret_key="secret key",
            content_id=faq_contents[0],
        )

        await save_content_feedback_to_db(
            feedback=content_feedback,
            asession=asession,
        )

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
    user1: int,
) -> None:
    end_date = datetime.now(timezone.utc)
    frequency, start_date = get_frequency_and_startdate(content_with_query_history)
    performance_stats = await retrieve_performance(
        user1,
        asession,
        n_top,
        start_date,
        end_date,
        frequency,
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
    user2: int,
    user1: int,
) -> None:
    end_date = datetime.now(timezone.utc)
    frequency, start_date = get_frequency_and_startdate(content_with_query_history)

    performance_stats = await retrieve_performance(
        user2,
        asession,
        1,
        start_date,
        end_date,
        frequency,
    )

    time_series = performance_stats.content_time_series
    assert len(time_series) == 0


async def test_drawer_data(
    content_with_query_history: DashboardTimeFilter,
    asession: AsyncSession,
    faq_contents: List[int],
    user1: int,
) -> None:
    end_date = datetime.now(timezone.utc)
    frequency, start_date = get_frequency_and_startdate(content_with_query_history)

    max_feedback_records = 10

    drawer_data = await get_content_details(
        user1, faq_contents[0], asession, start_date, end_date, frequency, 10
    )

    assert drawer_data.query_count == N_CONTENT_SHARED[0]
    assert drawer_data.positive_votes == np.ceil(len(N_CONTENT_SHARED) / 2)
    assert len(drawer_data.user_feedback) == min(
        len(N_CONTENT_SHARED), max_feedback_records
    )
    assert drawer_data.negative_votes == np.floor(len(N_CONTENT_SHARED) / 2)
