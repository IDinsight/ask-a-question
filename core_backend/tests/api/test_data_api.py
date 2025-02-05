"""This module contains tests for the data API endpoints."""

import random
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import pytest
from dateutil.relativedelta import relativedelta
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.question_answer.models import (
    save_content_feedback_to_db,
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

from .conftest import MockDatetime

N_CONTENT_FEEDBACKS = 2
N_DAYS_HISTORY = 10
N_RESPONSE_FEEDBACKS = 3


class TestContentDataAPI:
    """Tests for the content data API."""

    async def test_content_extract(
        self,
        api_key_workspace_data_api_1: str,
        api_key_workspace_data_api_2: str,
        client: TestClient,
        faq_contents_in_workspace_data_api_1: list[int],
    ) -> None:
        """Test the content extraction process.

        Parameters
        ----------
        api_key_workspace_data_api_1
            The API key of data API workspace 1.
        api_key_workspace_data_api_2
            The API key of data API workspace 2.
        client
            The test client.
        faq_contents_in_workspace_data_api_1
            The FAQ contents in data API workspace 1.
        """

        response = client.get(
            "/data-api/contents",
            headers={"Authorization": f"Bearer {api_key_workspace_data_api_1}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == len(faq_contents_in_workspace_data_api_1)
        response = client.get(
            "/data-api/contents",
            headers={"Authorization": f"Bearer {api_key_workspace_data_api_2}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 0

    @pytest.fixture
    async def faq_content_with_tags_admin_2_in_workspace_data_api_2(
        self, access_token_admin_data_api_2: str, client: TestClient
    ) -> AsyncGenerator[str, None]:
        """Create a FAQ content with tags for admin user 2.

        Parameters
        ----------
        access_token_admin_data_api_2
            The access token of the admin user 2 in data API workspace 2.
        client
            The test client.

        Yields
        ------
        AsyncGenerator[str, None]
            The tag name.
        """

        response = client.post(
            "/tag",
            json={"tag_name": "ADMIN_2_TAG"},
            headers={"Authorization": f"Bearer {access_token_admin_data_api_2}"},
        )
        json_response = response.json()
        tag_id = json_response["tag_id"]
        tag_name = json_response["tag_name"]
        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {access_token_admin_data_api_2}"},
            json={
                "content_metadata": {"metadata": "metadata"},
                "content_tags": [tag_id],
                "content_text": "text",
                "content_title": "title",
            },
        )
        json_response = response.json()

        yield tag_name

        client.delete(
            f"/content/{json_response['content_id']}",
            headers={"Authorization": f"Bearer {access_token_admin_data_api_2}"},
        )

        client.delete(
            f"/tag/{tag_id}",
            headers={"Authorization": f"Bearer {access_token_admin_data_api_2}"},
        )

    async def test_content_extract_with_tags(
        self,
        api_key_workspace_data_api_2: str,
        client: TestClient,
        faq_content_with_tags_admin_2_in_workspace_data_api_2: pytest.FixtureRequest,
    ) -> None:
        """Test the content extraction process with tags.

        Parameters
        ----------
        api_key_workspace_data_api_2
            The API key of data API workspace 2.
        client
            The test client.
        faq_content_with_tags_admin_2_in_workspace_data_api_2
            The fixture for the FAQ content with tags for admin user 2 in data API
            workspace 2.
        """

        response = client.get(
            "/data-api/contents",
            headers={"Authorization": f"Bearer {api_key_workspace_data_api_2}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1
        assert response.json()[0]["content_tags"][0] == "ADMIN_2_TAG"


class TestUrgencyRulesDataAPI:
    """Tests for the urgency rules data API."""

    async def test_urgency_rules_data_api(
        self,
        api_key_workspace_data_api_1: str,
        api_key_workspace_data_api_2: str,
        client: TestClient,
        urgency_rules_workspace_data_api_1: int,
    ) -> None:
        """Test the urgency rules data API.

        Parameters
        ----------
        api_key_workspace_data_api_1
            The API key of data API workspace 1.
        api_key_workspace_data_api_2
            The API key of data API workspace 2.
        client
            The test client.
        urgency_rules_workspace_data_api_1
            The number of urgency rules in data API workspace 1.
        """

        response = client.get(
            "/data-api/urgency-rules",
            headers={"Authorization": f"Bearer {api_key_workspace_data_api_1}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == urgency_rules_workspace_data_api_1

        response = client.get(
            "/data-api/urgency-rules",
            headers={"Authorization": f"Bearer {api_key_workspace_data_api_2}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 0

    async def test_urgency_rules_data_api_other_user(
        self,
        api_key_workspace_data_api_2: str,
        client: TestClient,
        urgency_rules_workspace_data_api_2: int,
    ) -> None:
        """Test the urgency rules data API with workspace 2.

        Parameters
        ----------
        api_key_workspace_data_api_2
            The API key of data API workspace 2.
        client
            The test client.
        urgency_rules_workspace_data_api_2
            The number of urgency rules in data API workspace 2.
        """

        response = client.get(
            "/data-api/urgency-rules",
            headers={"Authorization": f"Bearer {api_key_workspace_data_api_2}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == urgency_rules_workspace_data_api_2


class TestUrgencyQueryDataAPI:
    """Tests for the urgency query data API."""

    @pytest.fixture
    async def workspace_data_api_data_1(
        self,
        asession: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
        urgency_rules_workspace_data_api_1: int,
        workspace_data_api_id_1: int,
    ) -> AsyncGenerator[None, None]:
        """Create urgency query data for data API workspace 1.

        Parameters
        ----------
        asession
            The async session.
        monkeypatch
            The monkeypatch fixture.
        urgency_rules_workspace_data_api_1
            The number of urgency rules in the data API workspace 1.
        workspace_data_api_id_1
            The ID of the data API workspace 1.

        Yields
        ------
        AsyncGenerator[None, None]
            The urgency query data.
        """

        now = datetime.now(timezone.utc)
        dates = [now - relativedelta(days=x) for x in range(N_DAYS_HISTORY)]
        all_orm_objects: list[Any] = []

        for i, date in enumerate(dates):
            monkeypatch.setattr(
                "core_backend.app.urgency_detection.models.datetime",
                MockDatetime(date=date),
            )
            urgency_query = UrgencyQuery(message_text=f"query {i}")
            urgency_query_db = await save_urgency_query_to_db(
                asession=asession,
                feedback_secret_key="secret key",  # pragma: allowlist secret
                urgency_query=urgency_query,
                workspace_id=workspace_data_api_id_1,
            )
            all_orm_objects.append(urgency_query_db)
            is_urgent = i % 2 == 0

            urgency_response = UrgencyResponse(
                details={
                    1: UrgencyRuleCosineDistance(urgency_rule="rule1", distance=0.4)
                },
                is_urgent=is_urgent,
                matched_rules=["rule1", "rule2"],
            )
            urgency_response_db = await save_urgency_response_to_db(
                asession=asession,
                response=urgency_response,
                urgency_query_db=urgency_query_db,
            )
            all_orm_objects.append(urgency_response_db)

        yield

        for orm_object in reversed(all_orm_objects):
            await asession.delete(orm_object)
        await asession.commit()

    @pytest.fixture
    async def workspace_data_api_data_2(
        self,
        asession: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
        workspace_data_api_id_2: int,
    ) -> AsyncGenerator[int, None]:
        """Create urgency query data for data API workspace 2.

        Parameters
        ----------
        asession
            The async session.
        monkeypatch
            The monkeypatch fixture.
        workspace_data_api_id_2
            The ID of data API workspace 2.

        Yields
        ------
        AsyncGenerator[int, None]
            The number of days ago.
        """

        days_ago = random.randrange(N_DAYS_HISTORY)
        date = datetime.now(timezone.utc) - relativedelta(days=days_ago)
        monkeypatch.setattr(
            "core_backend.app.urgency_detection.models.datetime",
            MockDatetime(date=date),
        )
        urgency_query = UrgencyQuery(message_text="query")
        urgency_query_db = await save_urgency_query_to_db(
            asession=asession,
            feedback_secret_key="secret key",  # pragma: allowlist secret
            urgency_query=urgency_query,
            workspace_id=workspace_data_api_id_2,
        )

        yield days_ago

        await asession.delete(urgency_query_db)
        await asession.commit()

    def test_urgency_query_data_api(
        self,
        api_key_workspace_data_api_1: str,
        client: TestClient,
        workspace_data_api_data_1: pytest.FixtureRequest,
    ) -> None:
        """Test the urgency query data API.

        Parameters
        ----------
        api_key_workspace_data_api_1
            The API key of data API workspace 1.
        client
            The test client.
        workspace_data_api_data_1
            The data of the data API workspace 1.
        """

        response = client.get(
            "/data-api/urgency-queries",
            headers={"Authorization": f"Bearer {api_key_workspace_data_api_1}"},
            params={"start_date": "2021-01-01", "end_date": "2021-01-10"},
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize(
        "days_ago_start, days_ago_end",
        [[5, 1], [6, 4], [5, 5], [0, 0], [20, 14], [11, 0], [2, 5]],
    )
    def test_urgency_query_data_api_date_filter(
        self,
        days_ago_start: int,
        days_ago_end: int,
        api_key_workspace_data_api_1: str,
        client: TestClient,
        workspace_data_api_data_1: pytest.FixtureRequest,
    ) -> None:
        """Test the urgency query data API with date filtering.

        Parameters
        ----------
        days_ago_start
            The number of days ago to start.
        days_ago_end
            The number of days ago to end.
        api_key_workspace_data_api_1
            The API key of data API workspace 1.
        client
            The test client.
        workspace_data_api_data_1
            The data of data API workspace 1.
        """

        start_date = datetime.now(timezone.utc) - relativedelta(
            days=days_ago_start, seconds=2
        )
        end_date = datetime.now(timezone.utc) - relativedelta(
            days=days_ago_end, seconds=-2
        )
        date_format = "%Y-%m-%dT%H:%M:%S.%f%z"

        response = client.get(
            "/data-api/urgency-queries",
            headers={"Authorization": f"Bearer {api_key_workspace_data_api_1}"},
            params={
                "start_date": start_date.strftime(date_format),
                "end_date": end_date.strftime(date_format),
            },
        )
        assert response.status_code == status.HTTP_200_OK

        if days_ago_start > N_DAYS_HISTORY:
            if days_ago_end == 0:
                n_records = N_DAYS_HISTORY
            elif days_ago_end > N_DAYS_HISTORY:
                n_records = 0
            else:
                n_records = N_DAYS_HISTORY - days_ago_end + 1
        elif days_ago_start == N_DAYS_HISTORY:
            if days_ago_end > N_DAYS_HISTORY:
                n_records = 0
            else:
                n_records = N_DAYS_HISTORY - days_ago_end + 1
        # days_ago_start < N_DAYS_HISTORY
        elif days_ago_end > N_DAYS_HISTORY:
            n_records = 0
        elif days_ago_end == N_DAYS_HISTORY:
            n_records = 0
        elif days_ago_end > days_ago_start:
            n_records = 0
        # days_ago_end <= days_ago_start < N_DAYS_HISTORY
        else:
            n_records = days_ago_start - days_ago_end + 1

        assert len(response.json()) == n_records

    @pytest.mark.parametrize(
        "days_ago_start, days_ago_end",
        [[5, 1], [6, 4], [5, 5], [0, 0], [20, 14], [11, 0], [2, 5]],
    )
    def test_urgency_query_data_api_other_user(
        self,
        days_ago_start: int,
        days_ago_end: int,
        api_key_workspace_data_api_2: str,
        client: TestClient,
        workspace_data_api_data_2: int,
    ) -> None:
        """Test the urgency query data API with workspace 2.

        Parameters
        ----------
        days_ago_start
            The number of days ago to start.
        days_ago_end
            The number of days ago to end.
        api_key_workspace_data_api_2
            The API key of data API workspace 2.
        client
            The test client.
        workspace_data_api_data_2
            The data of data API workspace 2.
        """

        start_date = datetime.now(timezone.utc) - relativedelta(
            days=days_ago_start, seconds=2
        )
        end_date = datetime.now(timezone.utc) - relativedelta(
            days=days_ago_end, seconds=-2
        )
        date_format = "%Y-%m-%dT%H:%M:%S.%f%z"

        response = client.get(
            "/data-api/urgency-queries",
            headers={"Authorization": f"Bearer {api_key_workspace_data_api_2}"},
            params={
                "start_date": start_date.strftime(date_format),
                "end_date": end_date.strftime(date_format),
            },
        )
        assert response.status_code == status.HTTP_200_OK

        if days_ago_end <= workspace_data_api_data_2 <= days_ago_start:
            assert len(response.json()) == 1
        else:
            assert len(response.json()) == 0


class TestQueryDataAPI:
    """Tests for the query data API."""

    @pytest.fixture
    async def workspace_data_api_data_1(
        self,
        asession: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
        faq_contents_in_workspace_data_api_1: list[int],
        workspace_data_api_id_1: int,
    ) -> AsyncGenerator[None, None]:
        """Create query data for workspace 1.

        Parameters
        ----------
        asession
            The async session.
        monkeypatch
            The monkeypatch fixture.
        faq_contents_in_workspace_data_api_1
            The FAQ contents in data API workspace 1.
        workspace_data_api_id_1
            The ID of data API workspace 1.

        Yields
        ------
        AsyncGenerator[None, None]
            The data of workspace 1.
        """

        now = datetime.now(timezone.utc)
        dates = [now - relativedelta(days=x) for x in range(N_DAYS_HISTORY)]
        all_orm_objects: list[Any] = []

        for i, date in enumerate(dates):
            monkeypatch.setattr(
                "core_backend.app.question_answer.models.datetime",
                MockDatetime(date=date),
            )
            query = QueryBase(generate_llm_response=False, query_text=f"query {i}")
            query_db = await save_user_query_to_db(
                asession=asession,
                user_query=query,
                workspace_id=workspace_data_api_id_1,
            )
            all_orm_objects.append(query_db)
            if i % 2 == 0:
                response = QueryResponse(
                    feedback_secret_key="test_secret_key",
                    llm_response=None,
                    query_id=query_db.query_id,
                    search_results={
                        1: QuerySearchResult(
                            distance=0.5,
                            id=faq_contents_in_workspace_data_api_1[0],
                            text="text",
                            title="title",
                        )
                    },
                    session_id=None,
                )
                response_db = await save_query_response_to_db(
                    asession=asession,
                    response=response,
                    user_query_db=query_db,
                    workspace_id=workspace_data_api_id_1,
                )
                all_orm_objects.append(response_db)
                for i in range(N_RESPONSE_FEEDBACKS):
                    response_feedback = ResponseFeedbackBase(
                        feedback_secret_key="test_secret_key",
                        feedback_sentiment=FeedbackSentiment.POSITIVE,
                        feedback_text=f"feedback {i}",
                        query_id=response_db.query_id,
                        session_id=response_db.session_id,
                    )
                    response_feedback_db = await save_response_feedback_to_db(
                        asession=asession, feedback=response_feedback
                    )
                    all_orm_objects.append(response_feedback_db)
                for i in range(N_CONTENT_FEEDBACKS):
                    content_feedback = ContentFeedback(
                        content_id=faq_contents_in_workspace_data_api_1[0],
                        feedback_secret_key="test_secret_key",
                        feedback_sentiment=FeedbackSentiment.POSITIVE,
                        feedback_text=f"feedback {i}",
                        query_id=response_db.query_id,
                        session_id=response_db.session_id,
                    )
                    content_feedback_db = await save_content_feedback_to_db(
                        asession=asession, feedback=content_feedback
                    )
                    all_orm_objects.append(content_feedback_db)
            else:
                response_err = QueryResponseError(
                    error_message="error",
                    error_type=ErrorType.ALIGNMENT_TOO_LOW,
                    feedback_secret_key="test_secret_key",
                    llm_response=None,
                    query_id=query_db.query_id,
                    search_results={
                        1: QuerySearchResult(
                            distance=0.5,
                            id=faq_contents_in_workspace_data_api_1[0],
                            text="text",
                            title="title",
                        )
                    },
                    session_id=None,
                )
                response_err_db = await save_query_response_to_db(
                    asession=asession,
                    response=response_err,
                    user_query_db=query_db,
                    workspace_id=workspace_data_api_id_1,
                )
                all_orm_objects.append(response_err_db)

        # Return the data of workspace 1.
        yield

        # Clean up.
        for orm_object in reversed(all_orm_objects):
            await asession.delete(orm_object)
        await asession.commit()

    @pytest.fixture
    async def workspace_data_api_data_2(
        self,
        asession: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
        faq_contents_in_workspace_data_api_2: list[int],
        workspace_data_api_id_2: int,
    ) -> AsyncGenerator[int, None]:
        """Create query data for workspace 2.

        Parameters
        ----------
        asession
            The async session.
        monkeypatch
            The monkeypatch fixture.
        faq_contents_in_workspace_data_api_2
            The FAQ contents in data API workspace 2.
        workspace_data_api_id_2
            The ID of data API workspace 2.

        Yields
        ------
        AsyncGenerator[int, None]
            The number of days ago.
        """

        days_ago = random.randrange(N_DAYS_HISTORY)
        date = datetime.now(timezone.utc) - relativedelta(days=days_ago)
        monkeypatch.setattr(
            "core_backend.app.question_answer.models.datetime", MockDatetime(date=date)
        )
        query = QueryBase(generate_llm_response=False, query_text="query")
        query_db = await save_user_query_to_db(
            asession=asession, user_query=query, workspace_id=workspace_data_api_id_2
        )
        yield days_ago
        await asession.delete(query_db)
        await asession.commit()

    def test_query_data_api(
        self,
        api_key_workspace_data_api_1: str,
        client: TestClient,
        workspace_data_api_id_1: pytest.FixtureRequest,
    ) -> None:
        """Test the query data API for workspace 1.

        Parameters
        ----------
        api_key_workspace_data_api_1
            The API key of data API workspace 1.
        client
            The test client.
        workspace_data_api_id_1
            The data of the data API workspace 1.
        """

        response = client.get(
            "/data-api/queries",
            headers={"Authorization": f"Bearer {api_key_workspace_data_api_1}"},
            params={"start_date": "2021-01-01", "end_date": "2021-01-10"},
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize(
        "days_ago_start, days_ago_end",
        [[5, 1], [6, 4], [5, 5], [0, 0], [20, 14], [11, 0], [2, 5]],
    )
    def test_query_data_api_date_filter(
        self,
        days_ago_start: int,
        days_ago_end: int,
        api_key_workspace_data_api_1: str,
        client: TestClient,
        workspace_data_api_data_1: pytest.FixtureRequest,
    ) -> None:
        """Test the query data API with date filtering for the data API workspace.

        Parameters
        ----------
        days_ago_start
            The number of days ago to start.
        days_ago_end
            The number of days ago to end.
        api_key_workspace_data_api_1
            The API key of the data API workspace 1.
        client
            The test client.
        workspace_data_api_data_1
            The data of the data API workspace 1.
        """

        start_date = datetime.now(timezone.utc) - relativedelta(
            days=days_ago_start, seconds=2
        )
        end_date = datetime.now(timezone.utc) - relativedelta(
            days=days_ago_end, seconds=-2
        )
        date_format = "%Y-%m-%dT%H:%M:%S.%f%z"

        response = client.get(
            "/data-api/queries",
            headers={"Authorization": f"Bearer {api_key_workspace_data_api_1}"},
            params={
                "start_date": start_date.strftime(date_format),
                "end_date": end_date.strftime(date_format),
            },
        )
        assert response.status_code == status.HTTP_200_OK

        if days_ago_start > N_DAYS_HISTORY:
            if days_ago_end == 0:
                n_records = N_DAYS_HISTORY
            elif days_ago_end > N_DAYS_HISTORY:
                n_records = 0
            else:
                n_records = N_DAYS_HISTORY - days_ago_end + 1
        elif days_ago_start == N_DAYS_HISTORY:
            if days_ago_end > N_DAYS_HISTORY:
                n_records = 0
            else:
                n_records = N_DAYS_HISTORY - days_ago_end + 1
        # days_ago_start < N_DAYS_HISTORY
        elif days_ago_end > N_DAYS_HISTORY:
            n_records = 0
        elif days_ago_end == N_DAYS_HISTORY:
            n_records = 0
        elif days_ago_end > days_ago_start:
            n_records = 0
        # days_ago_end <= days_ago_start < N_DAYS_HISTORY
        else:
            n_records = days_ago_start - days_ago_end + 1

        assert len(response.json()) == n_records

    @pytest.mark.parametrize(
        "days_ago_start, days_ago_end",
        [[5, 1], [6, 4], [5, 5], [0, 0], [20, 14], [11, 0], [2, 5]],
    )
    def test_query_data_api_other_user(
        self,
        days_ago_start: int,
        days_ago_end: int,
        api_key_workspace_data_api_2: str,
        client: TestClient,
        workspace_data_api_data_2: int,
    ) -> None:
        """Test the query data API with workspace 2.

        Parameters
        ----------
        days_ago_start
            The number of days ago to start.
        days_ago_end
            The number of days ago to end.
        api_key_workspace_data_api_2
            The API key of data API workspace 2.
        client
            The test client.
        workspace_data_api_data_2
            The data of data API workspace 2.
        """

        start_date = datetime.now(timezone.utc) - relativedelta(
            days=days_ago_start, seconds=2
        )
        end_date = datetime.now(timezone.utc) - relativedelta(
            days=days_ago_end, seconds=-2
        )
        date_format = "%Y-%m-%dT%H:%M:%S.%f%z"

        response = client.get(
            "/data-api/queries",
            headers={"Authorization": f"Bearer {api_key_workspace_data_api_2}"},
            params={
                "start_date": start_date.strftime(date_format),
                "end_date": end_date.strftime(date_format),
            },
        )
        assert response.status_code == status.HTTP_200_OK

        if days_ago_end <= workspace_data_api_data_2 <= days_ago_start:
            assert len(response.json()) == 1
        else:
            assert len(response.json()) == 0
