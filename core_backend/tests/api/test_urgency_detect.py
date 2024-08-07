from typing import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.urgency_detection.config import URGENCY_CLASSIFIER
from core_backend.app.urgency_detection.routers import ALL_URGENCY_CLASSIFIERS
from core_backend.app.urgency_detection.schemas import UrgencyQuery, UrgencyResponse
from core_backend.tests.api.conftest import TEST_USERNAME, TEST_USERNAME_2


class TestUrgencyDetectionApiLimit:

    @pytest.mark.parametrize(
        "temp_user_api_key_and_api_quota",
        [
            {"username": "temp_user_ud_api_limit_0", "api_daily_quota": 0},
            {"username": "temp_user_ud__api_limit_2", "api_daily_quota": 2},
            {"username": "temp_user_ud_api_limit_5", "api_daily_quota": 5},
        ],
        indirect=True,
    )
    async def test_api_call_ud_quota_integer(
        self,
        client: TestClient,
        temp_user_api_key_and_api_quota: tuple[str, int],
    ) -> None:
        temp_api_key, api_daily_limit = temp_user_api_key_and_api_quota

        for _i in range(api_daily_limit):
            response = client.post(
                "/urgency-detect",
                json={"message_text": "Test question"},
                headers={"Authorization": f"Bearer {temp_api_key}"},
            )
            assert response.status_code == 200
        response = client.post(
            "/urgency-detect",
            json={"message_text": "Test question"},
            headers={"Authorization": f"Bearer {temp_api_key}"},
        )
        assert response.status_code == 429


class TestUrgencyDetectionToken:
    @pytest.mark.parametrize(
        "token, expected_status_code",
        [
            ("api_key_incorrect", 401),
            ("api_key_correct", 200),
        ],
    )
    def test_ud_response(
        self,
        token: str,
        expected_status_code: int,
        api_key_user1: str,
        client: TestClient,
        urgency_rules: pytest.FixtureRequest,
    ) -> None:
        request_token = api_key_user1 if token == "api_key_correct" else token
        response = client.post(
            "/urgency-detect",
            json={
                "message_text": (
                    "Is it normal to feel bloated after 2 burgers and a milkshake?"
                )
            },
            headers={"Authorization": f"Bearer {request_token}"},
        )
        assert response.status_code == expected_status_code

        if expected_status_code == 200:
            json_response = response.json()
            assert isinstance(json_response["is_urgent"], bool)
            if URGENCY_CLASSIFIER == "cosine_distance_classifier":
                distance = json_response["details"]["0"]["distance"]
                assert distance >= 0.0 and distance <= 1.0
            elif URGENCY_CLASSIFIER == "llm_entailment_classifier":
                probability = json_response["details"]["probability"]
                assert probability >= 0.0 and probability <= 1.0
            else:
                raise ValueError(
                    f"Unsupported urgency classifier: {URGENCY_CLASSIFIER}"
                )

    @pytest.mark.parametrize(
        "username, expect_found",
        [
            (TEST_USERNAME, True),
            (TEST_USERNAME_2, False),
        ],
    )
    def test_user2_access_user1_rules(
        self,
        client: TestClient,
        username: str,
        api_key_user1: str,
        api_key_user2: str,
        expect_found: bool,
    ) -> None:
        token = api_key_user1 if username == TEST_USERNAME else api_key_user2
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
                # assert is_urgent
                pass
            else:
                # user2 has no urgency rules so no flag
                assert not is_urgent


class TestUrgencyClassifiers:
    @pytest.mark.parametrize("classifier", ALL_URGENCY_CLASSIFIERS.values())
    async def test_classifier(
        self, admin_user, asession: AsyncSession, classifier: Callable
    ) -> None:
        urgency_query = UrgencyQuery(
            message_text="Is it normal to feel bloated after 2 burgers and a milkshake?"
        )
        classifier_response = await classifier(
            user_id=admin_user, urgency_query=urgency_query, asession=asession
        )

        assert isinstance(classifier_response, UrgencyResponse)
