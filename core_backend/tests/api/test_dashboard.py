from datetime import datetime
from typing import AsyncGenerator, Tuple

import pytest
from dateutil.relativedelta import relativedelta
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.dashboard.models import (
    get_content_feedback_stats,
    get_query_count_stats,
    get_response_feedback_stats,
    get_urgency_stats,
)
from core_backend.app.question_answer.models import (
    ContentFeedbackDB,
    QueryDB,
    ResponseFeedbackDB,
    save_content_feedback_to_db,
    save_response_feedback_to_db,
    save_user_query_to_db,
)
from core_backend.app.question_answer.schemas import (
    ContentFeedback,
    QueryBase,
    ResponseFeedbackBase,
)
from core_backend.app.schemas import FeedbackSentiment
from core_backend.app.urgency_detection.models import (
    UrgencyQueryDB,
    UrgencyResponseDB,
    save_urgency_query_to_db,
    save_urgency_response_to_db,
)
from core_backend.app.urgency_detection.schemas import UrgencyQuery, UrgencyResponse


class TestUrgencyDetectionStats:

    @pytest.fixture(scope="function", params=[(0, 0), (0, 1), (1, 0), (3, 5)])
    async def urgency_detection(
        self,
        request: pytest.FixtureRequest,
        asession: AsyncSession,
        user: pytest.FixtureRequest,
    ) -> AsyncGenerator[Tuple[int, int], None]:
        n_urgent, n_not_urgent = request.param
        data = [(f"Test urgent query {i}", True) for i in range(n_urgent)]
        data += [(f"Test not urgent query {i}", False) for i in range(n_not_urgent)]

        urgency_query_ids = []
        urgency_response_ids = []
        for message_text, is_urgent in data:
            urgency_query = UrgencyQuery(message_text=message_text)
            urgency_query_db = await save_urgency_query_to_db(
                1, "test_secret_key", urgency_query, asession
            )

            urgency_response = UrgencyResponse(
                is_urgent=is_urgent, failed_rules=[], details={}
            )
            await save_urgency_response_to_db(
                urgency_query_db, urgency_response, asession
            )

            urgency_query_ids.append(urgency_query_db.urgency_query_id)
            urgency_response_ids.append(urgency_query_db.urgency_query_id)

        yield (n_urgent, n_not_urgent)

        await self.delete_urgency_data(
            asession, urgency_query_ids, urgency_response_ids
        )

    async def delete_urgency_data(
        self,
        asession: AsyncSession,
        urgency_detection_ids: list[int],
        urgency_response_ids: list[int],
    ) -> None:
        delete_urgency_response = delete(UrgencyResponseDB).where(
            UrgencyResponseDB.urgency_response_id.in_(urgency_response_ids)
        )
        await asession.execute(delete_urgency_response)
        delete_urgency_query = delete(UrgencyQueryDB).where(
            UrgencyQueryDB.urgency_query_id.in_(urgency_detection_ids)
        )
        await asession.execute(delete_urgency_query)
        await asession.commit()

    async def test_urgency_detection_stats(
        self, urgency_detection: Tuple[int, int], asession: AsyncSession
    ) -> None:
        n_urgent, _ = urgency_detection

        start_date = datetime.now() - relativedelta(months=1)
        end_date = datetime.now() + relativedelta(months=1)

        stats = await get_urgency_stats(
            1,
            asession,
            start_date,
            end_date,
        )

        assert stats.n_urgent == n_urgent
        assert stats.percentage_increase == 0.0


class MockDatetime:
    def __init__(self, date: datetime):
        self.date = date

    def utcnow(self) -> datetime:
        return self.date


class TestQueryStats:

    @pytest.fixture(scope="function")
    async def queries_and_feedbacks(
        self,
        asession: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
        faq_contents: pytest.FixtureRequest,
    ) -> AsyncGenerator[None, None]:

        dates = [datetime.now() - relativedelta(days=x) for x in range(16)]
        for i, date in enumerate(dates):

            monkeypatch.setattr(
                "core_backend.app.question_answer.models.datetime", MockDatetime(date)
            )
            query = QueryBase(query_text="Test query")
            query_db = await save_user_query_to_db(
                1, "test_secret_key", query, asession
            )

            sentiment = (
                FeedbackSentiment.POSITIVE if i % 2 == 0 else FeedbackSentiment.NEGATIVE
            )
            response_feedback = ResponseFeedbackBase(
                query_id=query_db.query_id,
                feedback_sentiment=sentiment,
                feedback_secret_key="test_secret_key",
            )
            await save_response_feedback_to_db(response_feedback, asession)

            content_feedback = ContentFeedback(
                content_id=1,
                query_id=query_db.query_id,
                feedback_sentiment=sentiment,
                feedback_secret_key="test_secret_key",
            )
            await save_content_feedback_to_db(content_feedback, asession)

        yield

        delete_response_feedback = delete(ResponseFeedbackDB).where(
            ResponseFeedbackDB.query_id > 0
        )
        await asession.execute(delete_response_feedback)
        delete_content_feedback = delete(ContentFeedbackDB).where(
            ContentFeedbackDB.query_id > 0
        )
        await asession.execute(delete_content_feedback)
        delete_query = delete(QueryDB).where(QueryDB.query_id > 0)
        await asession.execute(delete_query)
        await asession.commit()

    async def test_query_stats(
        self, queries_and_feedbacks: pytest.FixtureRequest, asession: AsyncSession
    ) -> None:

        for _i, date in enumerate(
            [datetime.now() - relativedelta(days=x) for x in range(16)]
        ):
            start_date = date
            end_date = datetime.now()
            stats = await get_query_count_stats(
                1,
                asession,
                start_date,
                end_date,
            )

            assert stats.n_questions == _i

            stats_response_feedback = await get_response_feedback_stats(
                1,
                asession,
                start_date,
                end_date,
            )

            assert stats_response_feedback.n_positive == (_i + 1) // 2
            assert stats_response_feedback.n_negative == (_i) // 2

            await get_content_feedback_stats(
                1,
                asession,
                start_date,
                end_date,
            )
