"""HTTP tests for the dashboard endpoints.

Most tests replace the service function the endpoint calls (as imported in
`app.dashboard.router`) with a fake, so they check the HTTP contract only: auth,
validation, argument forwarding, status codes and response shape. A couple of
smoke tests go through the real service and database.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.exceptions import BadRequestError, NotFoundError
from app.dashboard.schemas import (
    AIFeedbackSummary,
    DashboardOverview,
    DashboardPerformance,
    DetailsDrawer,
    TimeFrequency,
    TopicsData,
)
from tests.conftest import TEST_WORKSPACE_NAME_1

ROUTER = "app.dashboard.router"

# Every dashboard endpoint (with a valid timeframe) and the service function it calls.
ENDPOINTS = [
    ("/dashboard/performance/week/1", "get_content_details_for_timeframe"),
    (
        "/dashboard/performance/week/1/ai-summary",
        "get_content_ai_summary_for_timeframe",
    ),
    ("/dashboard/performance/week", "get_performance_for_timeframe"),
    ("/dashboard/overview/week", "get_overview_for_timeframe"),
    ("/dashboard/insights/week/refresh", "get_insights_refresh_window"),
    ("/dashboard/insights/week", "get_insights"),
    ("/dashboard/topic_visualization/week", "create_topic_plot"),
]
PATHS = [path for path, _ in ENDPOINTS]


@pytest.fixture
def headers(access_token_admin_1: str) -> dict[str, str]:
    """Auth headers for admin user 1 (workspace 1).

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1.

    Returns
    -------
    dict[str, str]
        The `Authorization` header.
    """

    return {"Authorization": f"Bearer {access_token_admin_1}"}


def fake_service(
    monkeypatch: pytest.MonkeyPatch, name: str, **kwargs: Any
) -> AsyncMock:
    """Replace a service function imported in the router with an `AsyncMock`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    name
        The service function's name in `app.dashboard.router`.
    **kwargs
        Passed to `AsyncMock` (e.g. `return_value`, `side_effect`).

    Returns
    -------
    AsyncMock
        The fake.
    """

    fake = AsyncMock(**kwargs)
    monkeypatch.setattr(f"{ROUTER}.{name}", fake)
    return fake


class TestAuthAndValidation:
    """Requests rejected before reaching the service."""

    @pytest.mark.parametrize("path", PATHS)
    @pytest.mark.parametrize(
        "auth", [{}, {"Authorization": "Bearer not-a-jwt"}], ids=["none", "invalid"]
    )
    def test_requires_login(
        self, client: TestClient, path: str, auth: dict[str, str]
    ) -> None:
        """Missing or invalid tokens are rejected with 401.

        Parameters
        ----------
        client
            Test client.
        path
            The endpoint path.
        auth
            The request headers.
        """

        response = client.get(path, headers=auth)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("path", PATHS)
    def test_invalid_timeframe(
        self, client: TestClient, headers: dict[str, str], path: str
    ) -> None:
        """A timeframe outside `DashboardTimeFilter` is a 422.

        Parameters
        ----------
        client
            Test client.
        headers
            Auth headers.
        path
            The endpoint path.
        """

        response = client.get(path.replace("/week", "/decade"), headers=headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.parametrize(
        "path",
        [
            "/dashboard/performance/week/abc",
            "/dashboard/performance/week/abc/ai-summary",
            "/dashboard/performance/week?top_n=many",
            "/dashboard/overview/custom?frequency=Fortnight",
        ],
        ids=["content-id", "ai-summary-content-id", "top-n", "frequency"],
    )
    def test_invalid_params(
        self, client: TestClient, headers: dict[str, str], path: str
    ) -> None:
        """Badly typed path or query parameters are a 422.

        Parameters
        ----------
        client
            Test client.
        headers
            Auth headers.
        path
            The request path.
        """

        response = client.get(path, headers=headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize(
    "error, expected_status",
    [
        (BadRequestError("bad window"), status.HTTP_400_BAD_REQUEST),
        (NotFoundError("bad window"), status.HTTP_404_NOT_FOUND),
    ],
)
@pytest.mark.parametrize("path, service_name", ENDPOINTS)
def test_service_errors_are_mapped(
    client: TestClient,
    headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    service_name: str,
    error: Exception,
    expected_status: int,
) -> None:
    """Domain errors raised by the service become `{"detail": ...}` responses.

    Parameters
    ----------
    client
        Test client.
    headers
        Auth headers.
    monkeypatch
        Pytest monkeypatch fixture.
    path
        The endpoint path.
    service_name
        The service function the endpoint calls.
    error
        The error the service raises.
    expected_status
        The expected HTTP status.
    """

    fake_service(monkeypatch, service_name, side_effect=error)

    response = client.get(path, headers=headers)

    assert response.status_code == expected_status
    assert response.json() == {"detail": "bad window"}


class TestSuccess:
    """Successful requests forward their arguments and return the service result."""

    def test_content_details(
        self,
        client: TestClient,
        headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`GET /performance/{timeframe}/{content_id}` returns the drawer data.

        Parameters
        ----------
        client
            Test client.
        headers
            Auth headers.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        drawer = DetailsDrawer(
            daily_query_count_avg=1,
            negative_votes=0,
            positive_votes=2,
            query_count=3,
            time_series={},
            title="Title",
            user_feedback=[],
        )
        fake = fake_service(
            monkeypatch, "get_content_details_for_timeframe", return_value=drawer
        )

        response = client.get(
            "/dashboard/performance/custom/5",
            headers=headers,
            params={"start_date": "2025-01-01", "end_date": "2025-01-31"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == drawer.model_dump(mode="json")
        assert fake.await_args is not None
        assert dict(fake.await_args.kwargs) | {"asession": None} == {
            "asession": None,
            "content_id": 5,
            "end_date": "2025-01-31",
            "start_date": "2025-01-01",
            "timeframe": "custom",
            "workspace_name": TEST_WORKSPACE_NAME_1,
        }

    def test_ai_summary(
        self,
        client: TestClient,
        headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`GET .../ai-summary` returns the summary.

        Parameters
        ----------
        client
            Test client.
        headers
            Auth headers.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        fake = fake_service(
            monkeypatch,
            "get_content_ai_summary_for_timeframe",
            return_value=AIFeedbackSummary(ai_summary="Mostly positive."),
        )

        response = client.get(
            "/dashboard/performance/month/5/ai-summary", headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"ai_summary": "Mostly positive."}
        assert fake.await_args is not None
        kwargs = fake.await_args.kwargs
        assert (kwargs["content_id"], kwargs["timeframe"]) == (5, "month")
        assert (kwargs["start_date"], kwargs["end_date"]) == (None, None)

    def test_performance(
        self,
        client: TestClient,
        headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`GET /performance/{timeframe}` forwards `top_n`.

        Parameters
        ----------
        client
            Test client.
        headers
            Auth headers.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        fake = fake_service(
            monkeypatch,
            "get_performance_for_timeframe",
            return_value=DashboardPerformance(content_time_series=[]),
        )

        response = client.get(
            "/dashboard/performance/year", headers=headers, params={"top_n": 3}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"content_time_series": []}
        assert fake.await_args is not None
        kwargs = fake.await_args.kwargs
        assert (kwargs["top_n"], kwargs["timeframe"]) == (3, "year")
        assert kwargs["workspace_name"] == TEST_WORKSPACE_NAME_1

    def test_overview(
        self,
        client: TestClient,
        headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
        empty_overview: DashboardOverview,
    ) -> None:
        """`GET /overview/{timeframe}` forwards the custom window and frequency.

        Parameters
        ----------
        client
            Test client.
        headers
            Auth headers.
        monkeypatch
            Pytest monkeypatch fixture.
        empty_overview
            The overview the fake returns.
        """

        fake = fake_service(
            monkeypatch, "get_overview_for_timeframe", return_value=empty_overview
        )

        response = client.get(
            "/dashboard/overview/custom",
            headers=headers,
            params={
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "frequency": "Week",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert set(response.json()) == {
            "heatmap",
            "stats_cards",
            "time_series",
            "top_content",
        }
        assert fake.await_args is not None
        kwargs = fake.await_args.kwargs
        assert kwargs["frequency"] == TimeFrequency.Week
        assert (kwargs["start_date"], kwargs["end_date"]) == (
            "2025-01-01",
            "2025-01-31",
        )

    def test_refresh_insights_starts_background_task(
        self,
        client: TestClient,
        headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`GET /insights/{timeframe}/refresh` queues `refresh_insights`.

        Parameters
        ----------
        client
            Test client.
        headers
            Auth headers.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        workspace = SimpleNamespace(workspace_id=1, workspace_name="ws")
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        fake_service(
            monkeypatch,
            "get_insights_refresh_window",
            return_value=(workspace, start, end),
        )
        refresh = fake_service(monkeypatch, "refresh_insights")

        response = client.get("/dashboard/insights/day/refresh", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"detail": "Refresh task started in background."}
        # TestClient runs background tasks before returning the response.
        refresh.assert_awaited_once_with(
            end_date=end,
            redis=client.app.state.redis,  # type: ignore[attr-defined]
            start_date=start,
            timeframe="day",
            workspace_db=workspace,
        )

    def test_insights(
        self,
        client: TestClient,
        headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`GET /insights/{timeframe}` returns the cached topics.

        Parameters
        ----------
        client
            Test client.
        headers
            Auth headers.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        topics = TopicsData(data=[], refreshTimeStamp="", status="not_started")
        fake = fake_service(monkeypatch, "get_insights", return_value=topics)

        response = client.get("/dashboard/insights/week", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == topics.model_dump(mode="json")
        assert fake.await_args is not None
        assert fake.await_args.kwargs["redis"] is client.app.state.redis  # type: ignore[attr-defined]

    def test_topic_visualization(
        self,
        client: TestClient,
        headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`GET /topic_visualization/{timeframe}` returns the Bokeh JSON.

        Parameters
        ----------
        client
            Test client.
        headers
            Auth headers.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        plot = {"target_id": "myplot", "root_id": "x", "doc": {}}
        fake_service(monkeypatch, "create_topic_plot", return_value=plot)

        response = client.get("/dashboard/topic_visualization/week", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == plot


class TestRealService:
    """Smoke tests through the real service and database."""

    def test_overview(self, client: TestClient, headers: dict[str, str]) -> None:
        """The overview endpoint returns a well-formed payload for a real workspace.

        Parameters
        ----------
        client
            Test client.
        headers
            Auth headers.
        """

        response = client.get("/dashboard/overview/week", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["heatmap"]) == 12

    def test_custom_timeframe_without_dates(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        """A custom timeframe without dates is a 400 from the service.

        Parameters
        ----------
        client
            Test client.
        headers
            Auth headers.
        """

        response = client.get("/dashboard/performance/custom", headers=headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "start_date" in response.json()["detail"]
