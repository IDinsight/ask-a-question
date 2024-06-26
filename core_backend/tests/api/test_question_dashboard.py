import random
from functools import partial

import pytest
from fastapi.testclient import TestClient

from core_backend.app.question_dashboard.schemas import QuestionDashBoard


async def mock_dashboard_stats(
    user_id: int, asession: None, questions: tuple, upvotes: tuple
) -> QuestionDashBoard:
    """
    Function to monkeypatch question_dashboard.routersaz.get_dashboard_stats with
    random data
    """
    return QuestionDashBoard(
        six_months_questions=[
            random.randint(questions[0], questions[1]) for _ in range(6)
        ],
        six_months_upvotes=[random.randint(upvotes[0], upvotes[1]) for _ in range(6)],
    )


@pytest.mark.parametrize(
    "questions, upvotes",
    [
        ((0, 0), (0, 0)),
        ((500, 1000), (500, 1000)),
        ((1000, 2000), (0, 0)),
        ((0, 0), (1000, 2000)),
    ],
)
async def test_retrieve_question_dashboard(
    client: TestClient,
    fullaccess_token: str,
    monkeypatch: pytest.MonkeyPatch,
    questions: tuple,
    upvotes: tuple,
) -> None:
    mock_stats = partial(mock_dashboard_stats, questions=questions, upvotes=upvotes)
    monkeypatch.setattr(
        "core_backend.app.question_dashboard.routers.get_dashboard_stats", mock_stats
    )
    response = client.get(
        "/dashboard/question_stats",
        headers={"Authorization": f"Bearer {fullaccess_token}"},
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data["six_months_questions"]) == 6
    assert len(data["six_months_upvotes"]) == 6
    assert all(value >= questions[0] for value in data["six_months_questions"])
    assert all(value >= upvotes[0] for value in data["six_months_upvotes"])
    assert all(value <= questions[1] for value in data["six_months_questions"])
    assert all(value <= upvotes[1] for value in data["six_months_upvotes"])
