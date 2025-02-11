"""This module contains tests for the urgency detection API."""

from typing import Any, Callable

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from core_backend.app.urgency_detection.config import URGENCY_CLASSIFIER
from core_backend.app.urgency_detection.models import UrgencyQueryDB, UrgencyResponseDB
from core_backend.app.urgency_detection.routers import ALL_URGENCY_CLASSIFIERS
from core_backend.app.urgency_detection.schemas import UrgencyQuery, UrgencyResponse
from core_backend.app.workspaces.utils import get_workspace_by_workspace_name
from core_backend.tests.api.conftest import TEST_ADMIN_USERNAME_1, TEST_ADMIN_USERNAME_2


class TestUrgencyDetectionApiLimit:
    """Tests for the urgency detection API rate limiting."""

    @pytest.mark.parametrize(
        "temp_workspace_api_key_and_api_quota",
        [
            {
                "api_daily_quota": 0,
                "username": "temp_user_ud_api_limit_0",
                "workspace_name": "temp_workspace_ud_api_limit_0",
            },
            {
                "api_daily_quota": 2,
                "username": "temp_user_ud__api_limit_2",
                "workspace_name": "temp_workspace_ud__api_limit_2",
            },
            {
                "api_daily_quota": 5,
                "username": "temp_user_ud_api_limit_5",
                "workspace_name": "temp_workspace_ud_api_limit_5",
            },
        ],
        indirect=True,
    )
    async def test_api_call_ud_quota_integer(
        self, client: TestClient, temp_workspace_api_key_and_api_quota: tuple[str, int]
    ) -> None:
        """Test the urgency detection API rate limiting.

        Parameters
        ----------
        client
            Test client.
        temp_workspace_api_key_and_api_quota
            Temporary workspace API key and API quota.
        """

        temp_api_key, api_daily_limit = temp_workspace_api_key_and_api_quota

        for _ in range(api_daily_limit):
            response = client.post(
                "/urgency-detect",
                json={"message_text": "Test question"},
                headers={"Authorization": f"Bearer {temp_api_key}"},
            )
            assert response.status_code == status.HTTP_200_OK

        response = client.post(
            "/urgency-detect",
            headers={"Authorization": f"Bearer {temp_api_key}"},
            json={"message_text": "Test question"},
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestUrgencyDetectionToken:
    """Tests for the urgency detection API with different tokens."""

    @pytest.mark.parametrize(
        "token, expected_status_code",
        [("api_key_incorrect", 401), ("api_key_correct", 200)],
    )
    def test_ud_response(
        self,
        token: str,
        expected_status_code: int,
        api_key_workspace_1: str,
        client: TestClient,
        urgency_rules_workspace_1: pytest.FixtureRequest,
    ) -> None:
        """Test the urgency detection API with different tokens.

        Parameters
        ----------
        token
            Token.
        expected_status_code
            Expected status code.
        api_key_workspace_1
            API key for workspace 1.
        client
            Test client.
        urgency_rules_workspace_1
            Urgency rules for workspace 1.

        Raises
        ------
        ValueError
            If the urgency classifier is not supported.
        """

        request_token = api_key_workspace_1 if token == "api_key_correct" else token
        response = client.post(
            "/urgency-detect",
            headers={"Authorization": f"Bearer {request_token}"},
            json={
                "message_text": (
                    "Is it normal to feel bloated after 2 burgers and a milkshake?"
                )
            },
        )
        assert response.status_code == expected_status_code

        if expected_status_code == status.HTTP_200_OK:
            json_response = response.json()
            assert isinstance(json_response["is_urgent"], bool)
            if URGENCY_CLASSIFIER == "cosine_distance_classifier":
                distance = json_response["details"]["0"]["distance"]
                assert 0.0 <= distance <= 1.0
            elif URGENCY_CLASSIFIER == "llm_entailment_classifier":
                probability = json_response["details"]["probability"]
                assert 0.0 <= probability <= 1.0
            else:
                raise ValueError(
                    f"Unsupported urgency classifier: {URGENCY_CLASSIFIER}"
                )

    @pytest.mark.parametrize(
        "username, expect_found",
        [(TEST_ADMIN_USERNAME_1, True), (TEST_ADMIN_USERNAME_2, False)],
    )
    def test_admin_2_access_admin_1_rules(
        self,
        username: str,
        expect_found: bool,
        api_key_workspace_1: str,
        api_key_workspace_2: str,
        client: TestClient,
        db_session: Session,
        workspace_1_id: int,
        workspace_2_id: int,
    ) -> None:
        """Test that an admin user can access the urgency rules of another admin user.

        Parameters
        ----------
        username
            The user name.
        expect_found
            Specifies whether the urgency rules are expected to be found.
        api_key_workspace_1
            API key for workspace 1.
        api_key_workspace_2
            API key for workspace 2.
        client
            Test client.
        db_session
            Database session.
        workspace_1_id
            The ID of workspace 1.
        workspace_2_id
            The ID of workspace 2.
        """

        token, workspace_id = (
            (api_key_workspace_1, workspace_1_id)
            if username == TEST_ADMIN_USERNAME_1
            else (api_key_workspace_2, workspace_2_id)
        )
        response = client.post(
            "/urgency-detect",
            headers={"Authorization": f"Bearer {token}"},
            json={"message_text": "has trouble breathing"},
        )
        assert response.status_code == status.HTTP_200_OK

        is_urgent = response.json()["is_urgent"]
        if expect_found:
            # The breathing query should flag as urgent for admin user 1. See
            # data/urgency_rules.json which is loaded by the urgency_rules fixture.
            # Assert is_urgent.
            pass
        else:
            # Admin user 2 has no urgency rules so no flag.
            assert not is_urgent

        # Delete urgency queries.
        stmt = delete(UrgencyQueryDB).where(UrgencyQueryDB.workspace_id == workspace_id)
        db_session.execute(stmt)

        # Delete urgency query responses.
        stmt = delete(UrgencyResponseDB).where(
            UrgencyResponseDB.workspace_id == workspace_id
        )
        db_session.execute(stmt)

        db_session.commit()


class TestUrgencyClassifiers:
    """Tests for the urgency classifiers."""

    @pytest.mark.parametrize("classifier", ALL_URGENCY_CLASSIFIERS.values())
    async def test_classifier(
        self,
        admin_user_1_in_workspace_1: dict[str, Any],
        asession: AsyncSession,
        classifier: Callable,
    ) -> None:
        """Test the urgency classifier.

        Parameters
        ----------
        admin_user_1_in_workspace_1
            Admin user in workspace 1.
        asession
            Async session.
        classifier
            Urgency classifier.
        """

        workspace_db = await get_workspace_by_workspace_name(
            asession=asession,
            workspace_name=admin_user_1_in_workspace_1["workspace_name"],
        )
        workspace_id = workspace_db.workspace_id
        urgency_query = UrgencyQuery(
            message_text="Is it normal to feel bloated after 2 burgers and a milkshake?"
        )
        classifier_response = await classifier(
            asession=asession, urgency_query=urgency_query, workspace_id=workspace_id
        )

        assert isinstance(classifier_response, UrgencyResponse)
