from typing import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.auth.config import QUESTION_ANSWER_SECRET
from core_backend.app.database import get_async_session
from core_backend.app.urgency_detection.routers import ALL_URGENCY_CLASSIFIERS
from core_backend.app.urgency_detection.schemas import UrgencyQuery, UrgencyResponse


class TestUrgencyDetectionToken:
    @pytest.mark.parametrize(
        "token, expected_status_code",
        [(f"{QUESTION_ANSWER_SECRET}_incorrect", 401), (QUESTION_ANSWER_SECRET, 200)],
    )
    async def test_ud_response(
        self,
        token: str,
        expected_status_code: int,
        client: TestClient,
        urgency_rules: pytest.FixtureRequest,
    ) -> None:
        response = client.post(
            "/urgency-detect",
            json={
                "message_text": (
                    "Is it normal to feel bloated after 2 burgers and a milkshake?"
                )
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == expected_status_code

        if expected_status_code == 200:
            json_content_response = response.json()["details"]
            assert len(json_content_response.keys()) == urgency_rules


class TestUrgencyClassifiers:
    @pytest.fixture(scope="class")
    async def asession(self) -> AsyncSession:
        async for session in get_async_session():
            yield session

        await session.close()

    @pytest.mark.parametrize("classifier", ALL_URGENCY_CLASSIFIERS.values())
    async def test_classifier(
        self, asession: AsyncSession, classifier: Callable
    ) -> None:
        urgency_query = UrgencyQuery(
            message_text="Is it normal to feel bloated after 2 burgers and a milkshake?"
        )
        classifier_response = await classifier(asession, urgency_query)

        assert isinstance(classifier_response, UrgencyResponse)
