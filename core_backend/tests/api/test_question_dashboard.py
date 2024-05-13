import pytest
from fastapi.testclient import TestClient

from .conftest import mock_dashboard_stats


def test_retrieve_question_dashboard(
    client: TestClient,
    fullaccess_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core_backend.app.question_dashboard.models.get_dashboard_stats",
        mock_dashboard_stats,
    )
    response = client.get(
        "/dashboard/question_stats",
        headers={"Authorization": f"Bearer {fullaccess_token}"},
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data["six_months_questions"]) == 6
    assert len(data["six_months_upvotes"]) == 6
