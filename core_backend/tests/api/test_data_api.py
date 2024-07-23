import random
from datetime import datetime, timezone, tzinfo
from typing import Any, AsyncGenerator, List, Optional

import pytest
from dateutil.relativedelta import relativedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.question_answer.models import (
    save_content_feedback_to_db,
    save_query_response_error_to_db,
    save_query_response_to_db,
    save_response_feedback_to_db,
    save_user_query_to_db,
)
from core_backend.app.question_answer.schemas import (
    ContentFeedback,
    ErrorType,
    QueryBase,
    QueryResponse,
    QueryResponseError,
    ResponseFeedbackBase,
)
from core_backend.app.schemas import FeedbackSentiment, QuerySearchResult
from core_backend.app.urgency_detection.models import (
    save_urgency_query_to_db,
    save_urgency_response_to_db,
)
from core_backend.app.urgency_detection.schemas import UrgencyQuery, UrgencyResponse
from core_backend.app.urgency_rules.schemas import UrgencyRuleCosineDistance

N_RESPONSE_FEEDBACKS = 3
N_CONTENT_FEEDBACKS = 2
N_DAYS_HISTORY = 10


class MockDatetime:
    def __init__(self, date: datetime):
        self.date = date

    def now(self, tz: Optional[tzinfo] = None) -> datetime:
        if tz is not None:
            return self.date.astimezone(tz)
        return self.date


class TestUrgencyQueryDataAPI:
    @pytest.fixture
    async def user1_data(
        self,
        monkeypatch: pytest.MonkeyPatch,
        asession: AsyncSession,
        urgency_rules: int,
    ) -> AsyncGenerator[None, None]:
        dates = [
            datetime.now(timezone.utc) - relativedelta(days=x)
            for x in range(N_DAYS_HISTORY)
        ]
        all_orm_objects: List[Any] = []

        for i, date in enumerate(dates):
            monkeypatch.setattr(
                "core_backend.app.urgency_detection.models.datetime", MockDatetime(date)
            )
            urgency_query = UrgencyQuery(message_text=f"query {i}")
            urgency_query_db = await save_urgency_query_to_db(
                1, "secret_key", urgency_query, asession
            )
            all_orm_objects.append(urgency_query_db)
            is_urgent = i % 2 == 0

            urgency_response = UrgencyResponse(
                is_urgent=is_urgent,
                matched_rules=["rule1", "rule2"],
                details={
                    1: UrgencyRuleCosineDistance(urgency_rule="rule1", distance=0.4)
                },
            )
            urgency_response_db = await save_urgency_response_to_db(
                urgency_query_db, urgency_response, asession
            )
            all_orm_objects.append(urgency_response_db)

        yield

        for orm_object in reversed(all_orm_objects):
            await asession.delete(orm_object)
        await asession.commit()

    @pytest.fixture
    async def user2_data(
        self,
        monkeypatch: pytest.MonkeyPatch,
        asession: AsyncSession,
    ) -> AsyncGenerator[int, None]:

        days_ago = random.randrange(N_DAYS_HISTORY)
        date = datetime.now(timezone.utc) - relativedelta(days=days_ago)
        monkeypatch.setattr(
            "core_backend.app.urgency_detection.models.datetime", MockDatetime(date)
        )
        urgency_query = UrgencyQuery(message_text="query")
        urgency_query_db = await save_urgency_query_to_db(
            2, "secret_key", urgency_query, asession
        )
        yield days_ago
        await asession.delete(urgency_query_db)
        await asession.commit()

    def test_urgency_query_data_api(
        self,
        user1_data: pytest.FixtureRequest,
        client: TestClient,
    ) -> None:

        response = client.get(
            "/data-api/urgency-queries",
            headers={"Authorization": "Bearer test_api_key"},
            params={"start_date": "2021-01-01T00:00", "end_date": "2021-01-10T00:00"},
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "start_day, end_day", [[5, 1], [6, 4], [5, 5], [0, 0], [20, 14], [11, 0]]
    )
    def test_urgency_query_data_api_date_filter(
        self,
        start_day: int,
        end_day: int,
        client: TestClient,
        user1_data: pytest.FixtureRequest,
    ) -> None:

        start_date = datetime.now(timezone.utc) - relativedelta(days=start_day)
        end_date = datetime.now(timezone.utc) - relativedelta(days=end_day)
        date_format = "%Y-%m-%dT%H:%M:%S.%f"

        response = client.get(
            "/data-api/urgency-queries",
            headers={"Authorization": "Bearer test_api_key"},
            params={
                "start_date": start_date.strftime(date_format),
                "end_date": end_date.strftime(date_format),
            },
        )
        assert response.status_code == 200

        data_start_date = min(start_day, N_DAYS_HISTORY)
        data_end_date = min(end_day, N_DAYS_HISTORY)
        n_records = (
            data_start_date - data_end_date if data_start_date > data_end_date else 0
        )
        assert len(response.json()) == n_records

    @pytest.mark.parametrize(
        "start_day, end_day", [[5, 1], [6, 4], [5, 5], [0, 0], [20, 14], [11, 0]]
    )
    def test_urgency_query_data_api_other_user(
        self,
        start_day: int,
        end_day: int,
        client: TestClient,
        user1_data: pytest.FixtureRequest,
        user2_data: int,
    ) -> None:

        start_date = datetime.now(timezone.utc) - relativedelta(days=start_day)
        end_date = datetime.now(timezone.utc) - relativedelta(days=end_day)
        date_format = "%Y-%m-%dT%H:%M:%S.%f"

        response = client.get(
            "/data-api/urgency-queries",
            headers={"Authorization": "Bearer test_api_key_2"},
            params={
                "start_date": start_date.strftime(date_format),
                "end_date": end_date.strftime(date_format),
            },
        )
        assert response.status_code == 200

        if end_day <= user2_data < start_day:
            assert len(response.json()) == 1
        else:
            assert len(response.json()) == 0


class TestQueryDataAPI:
    @pytest.fixture
    async def user1_data(
        self,
        monkeypatch: pytest.MonkeyPatch,
        asession: AsyncSession,
        faq_contents: List[int],
    ) -> AsyncGenerator[None, None]:
        dates = [
            datetime.now(timezone.utc) - relativedelta(days=x)
            for x in range(N_DAYS_HISTORY)
        ]
        all_orm_objects: List[Any] = []

        for i, date in enumerate(dates):
            monkeypatch.setattr(
                "core_backend.app.question_answer.models.datetime", MockDatetime(date)
            )
            query = QueryBase(query_text=f"query {i}")
            query_db = await save_user_query_to_db(
                user_id=1,
                user_query=query,
                asession=asession,
            )
            all_orm_objects.append(query_db)
            if i % 2 == 0:
                response = QueryResponse(
                    query_id=query_db.query_id,
                    llm_response=None,
                    search_results={
                        1: QuerySearchResult(
                            title="title",
                            text="text",
                            id=faq_contents[0],
                            distance=0.5,
                        )
                    },
                    feedback_secret_key="test_secret_key",
                )
                response_db = await save_query_response_to_db(
                    query_db, response, asession
                )
                all_orm_objects.append(response_db)
                for i in range(N_RESPONSE_FEEDBACKS):
                    response_feedback = ResponseFeedbackBase(
                        query_id=response_db.query_id,
                        feedback_text=f"feedback {i}",
                        feedback_sentiment=FeedbackSentiment.POSITIVE,
                        feedback_secret_key="test_secret_key",
                    )
                    response_feedback_db = await save_response_feedback_to_db(
                        response_feedback, asession
                    )
                    all_orm_objects.append(response_feedback_db)
                for i in range(N_CONTENT_FEEDBACKS):
                    content_feedback = ContentFeedback(
                        query_id=response_db.query_id,
                        content_id=faq_contents[0],
                        feedback_text=f"feedback {i}",
                        feedback_sentiment=FeedbackSentiment.POSITIVE,
                        feedback_secret_key="test_secret_key",
                    )
                    content_feedback_db = await save_content_feedback_to_db(
                        content_feedback, asession
                    )
                    all_orm_objects.append(content_feedback_db)
            else:
                response_err = QueryResponseError(
                    query_id=query_db.query_id,
                    error_message="error",
                    error_type=ErrorType.ALIGNMENT_TOO_LOW,
                )
                response_err_db = await save_query_response_error_to_db(
                    query_db, response_err, asession
                )
                all_orm_objects.append(response_err_db)

        # Return the data of user1
        yield

        # Clean up
        for orm_object in reversed(all_orm_objects):
            await asession.delete(orm_object)
        await asession.commit()

    @pytest.fixture
    async def user2_data(
        self,
        monkeypatch: pytest.MonkeyPatch,
        asession: AsyncSession,
        faq_contents: List[int],
    ) -> AsyncGenerator[int, None]:
        days_ago = random.randrange(N_DAYS_HISTORY)
        date = datetime.now(timezone.utc) - relativedelta(days=days_ago)
        monkeypatch.setattr(
            "core_backend.app.question_answer.models.datetime", MockDatetime(date)
        )
        query = QueryBase(query_text="query")
        query_db = await save_user_query_to_db(
            user_id=2,
            user_query=query,
            asession=asession,
        )
        yield days_ago
        await asession.delete(query_db)
        await asession.commit()

    def test_query_data_api(
        self,
        user1_data: pytest.FixtureRequest,
        client: TestClient,
    ) -> None:
        response = client.get(
            "/data-api/queries",
            headers={"Authorization": "Bearer test_api_key"},
            params={"start_date": "2021-01-01T00:00", "end_date": "2021-01-10T00:00"},
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "start_day, end_day", [[5, 1], [6, 4], [5, 5], [0, 0], [20, 14], [11, 0]]
    )
    def test_query_data_api_date_filter(
        self,
        start_day: int,
        end_day: int,
        client: TestClient,
        user1_data: pytest.FixtureRequest,
    ) -> None:
        start_date = datetime.now(timezone.utc) - relativedelta(days=start_day)
        end_date = datetime.now(timezone.utc) - relativedelta(days=end_day)
        date_format = "%Y-%m-%dT%H:%M:%S.%f"

        response = client.get(
            "/data-api/queries",
            headers={"Authorization": "Bearer test_api_key"},
            params={
                "start_date": start_date.strftime(date_format),
                "end_date": end_date.strftime(date_format),
            },
        )
        assert response.status_code == 200

        data_start_date = min(start_day, N_DAYS_HISTORY)
        data_end_date = min(end_day, N_DAYS_HISTORY)
        n_records = (
            data_start_date - data_end_date if data_start_date > data_end_date else 0
        )

        assert len(response.json()) == n_records

    @pytest.mark.parametrize(
        "start_day, end_day", [[5, 1], [6, 4], [5, 5], [0, 0], [20, 14], [11, 0]]
    )
    def test_query_data_api_other_user(
        self,
        start_day: int,
        end_day: int,
        client: TestClient,
        user1_data: pytest.FixtureRequest,
        user2_data: int,
    ) -> None:
        start_date = datetime.now(timezone.utc) - relativedelta(days=start_day)
        end_date = datetime.now(timezone.utc) - relativedelta(days=end_day)
        date_format = "%Y-%m-%dT%H:%M:%S.%f"

        response = client.get(
            "/data-api/queries",
            headers={"Authorization": "Bearer test_api_key_2"},
            params={
                "start_date": start_date.strftime(date_format),
                "end_date": end_date.strftime(date_format),
            },
        )
        assert response.status_code == 200

        if end_day <= user2_data < start_day:
            assert len(response.json()) == 1
        else:
            assert len(response.json()) == 0
