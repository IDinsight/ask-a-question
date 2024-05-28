from typing import AsyncGenerator, Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.database import get_async_session
from core_backend.app.urgency_detection.routers import ALL_URGENCY_CLASSIFIERS
from core_backend.app.urgency_detection.schemas import UrgencyQuery, UrgencyResponse
from core_backend.tests.api.conftest import (
    TEST_USER_API_KEY,
    TEST_USER_API_KEY_2,
    TEST_USER_ID,
)


class TestUrgencyDetectionToken:
    @pytest.mark.parametrize(
        "token, expected_status_code",
        [
            (f"{TEST_USER_API_KEY}_incorrect", 401),
            (TEST_USER_API_KEY, 200),
        ],
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

    @pytest.mark.parametrize(
        "token, expect_found",
        [
            (TEST_USER_API_KEY, True),
            (TEST_USER_API_KEY_2, False),
        ],
    )
    async def test_user2_access_user1_rules(
        self,
        client: TestClient,
        token: str,
        expect_found: bool,
    ) -> None:
        response = client.post(
            "/urgency-detect",
            json={"message_text": "has trouble breathing"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        if response.status_code == 200:
            is_urgent = response.json()["is_urgent"]
            if expect_found:
                # the breathing query should flag as urgent for user1. See
                # data/urgency_rules.json which is loaded by the urgency_rules fixture.
                assert is_urgent
            else:
                # user2 has no urgency rules so no flag
                assert not is_urgent


class TestUrgencyClassifiers:
    @pytest.fixture(scope="function")
    async def asession(self) -> AsyncGenerator[AsyncSession, None]:
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
        classifier_response = await classifier(
            user_id=TEST_USER_ID, urgency_query=urgency_query, asession=asession
        )

        assert isinstance(classifier_response, UrgencyResponse)
