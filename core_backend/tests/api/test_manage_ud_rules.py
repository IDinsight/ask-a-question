"""This module contains tests for urgency rules endpoints."""

# pylint: disable=W0621
from datetime import datetime, timezone
from typing import Generator

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from core_backend.app.urgency_rules.models import UrgencyRuleDB
from core_backend.app.urgency_rules.routers import _convert_record_to_schema

from .conftest import async_fake_embedding

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


@pytest.fixture(
    scope="function",
    params=[
        ("test ud rule 1 - no metadata", {}),
        ("test ud rule 2 - with metadata", {"meta_key": "meta_value"}),
    ],
)
def existing_rule_id_in_workspace_1(
    access_token_admin_1: str, client: TestClient, request: pytest.FixtureRequest
) -> Generator[str, None, None]:
    """Create a new urgency rule in workspace 1 and return the rule ID.

    Parameters
    ----------
    access_token_admin_1
        Access token for the admin user in workspace 1.
    client
        Test client for the FastAPI application.
    request
        Pytest fixture request object.

    Yields
    ------
    Generator[str, None, None]
        The urgency rule ID.
    """

    response = client.post(
        "/urgency-rules",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
        json={
            "urgency_rule_metadata": request.param[1],
            "urgency_rule_text": request.param[0],
        },
    )
    rule_id = response.json()["urgency_rule_id"]

    yield rule_id

    client.delete(
        f"/urgency-rules/{rule_id}",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )


class TestManageUDRules:
    """Tests for managing urgency rules."""

    @pytest.mark.parametrize(
        "urgency_rule_text, urgency_rule_metadata",
        [("test rule 3", {}), ("test rule 4", {"meta_key": "meta_value"})],
    )
    def test_create_and_delete_ud_rules(
        self,
        access_token_admin_1: str,
        client: TestClient,
        urgency_rule_metadata: dict,
        urgency_rule_text: str,
    ) -> None:
        """Test creating and deleting urgency rules.

        Parameters
        ----------
        access_token_admin_1
            Access token for the admin user in workspace 1.
        client
            Test client for the FastAPI application.
        urgency_rule_metadata
            Metadata for the urgency rule.
        urgency_rule_text
            Text for the urgency rule.
        """

        response = client.post(
            "/urgency-rules",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "urgency_rule_metadata": urgency_rule_metadata,
                "urgency_rule_text": urgency_rule_text,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["urgency_rule_metadata"] == urgency_rule_metadata
        assert "urgency_rule_id" in json_response
        assert "workspace_id" in json_response

        response = client.delete(
            f"/urgency-rules/{json_response['urgency_rule_id']}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize(
        "urgency_rule_text, urgency_rule_metadata",
        [
            ("test rule 3 - edited", {}),
            (
                "test rule 4 - edited",
                {"new_meta_key": "new meta_value", "meta_key": "meta_value_edited #2"},
            ),
        ],
    )
    def test_edit_and_retrieve_ud_rules(
        self,
        access_token_admin_1: str,
        client: TestClient,
        existing_rule_id_in_workspace_1: int,
        urgency_rule_metadata: dict,
        urgency_rule_text: str,
    ) -> None:
        """Test editing and retrieving urgency rules.

        Parameters
        ----------
        access_token_admin_1
            Access token for the admin user in workspace 1.
        client
            Test client for the FastAPI application.
        existing_rule_id_in_workspace_1
            ID of an existing urgency rule in workspace 1.
        urgency_rule_metadata
            Metadata for the urgency rule.
        urgency_rule_text
            Text for the urgency rule.
        """

        response = client.put(
            f"/urgency-rules/{existing_rule_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "urgency_rule_metadata": urgency_rule_metadata,
                "urgency_rule_text": urgency_rule_text,
            },
        )

        assert response.status_code == status.HTTP_200_OK

        response = client.get(
            f"/urgency-rules/{existing_rule_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert response.status_code == status.HTTP_200_OK

        json_response = response.json()
        assert json_response["urgency_rule_text"] == urgency_rule_text
        edited_metadata = json_response["urgency_rule_metadata"]
        assert all(edited_metadata[k] == v for k, v in urgency_rule_metadata.items())

    def test_edit_ud_rules_not_found(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test editing a non-existent urgency rule.

        Parameters
        ----------
        access_token_admin_1
            Access token for the admin user in workspace 1.
        client
            Test client for the FastAPI application.
        """

        response = client.put(
            "/urgency-rules/12345",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "urgency_rule_metadata": {"key": "value"},
                "urgency_rule_text": "sample text",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_ud_rules(
        self,
        access_token_admin_1: str,
        client: TestClient,
        existing_rule_id_in_workspace_1: int,
    ) -> None:
        """Test listing urgency rules.

        Parameters
        ----------
        access_token_admin_1
            Access token for the admin user in workspace 1.
        client
            Test client for the FastAPI application.
        existing_rule_id_in_workspace_1
            ID of an existing urgency rule in workspace 1.
        """

        response = client.get(
            "/urgency-rules/",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) > 0

    def test_delete_ud_rules(
        self,
        access_token_admin_1: str,
        client: TestClient,
        existing_rule_id_in_workspace_1: int,
    ) -> None:
        """Test deleting urgency rules.

        Parameters
        ----------
        access_token_admin_1
            Access token for the admin user in workspace 1.
        client
            Test client for the FastAPI application.
        existing_rule_id_in_workspace_1
            ID of an existing urgency rule in workspace 1.
        """

        response = client.delete(
            f"/urgency-rules/{existing_rule_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert response.status_code == status.HTTP_200_OK


class TestMultiUserManageUDRules:
    """Tests for managing urgency rules by multiple users."""

    @staticmethod
    def test_admin_2_get_admin_1_ud_rule(
        access_token_admin_2: str,
        client: TestClient,
        existing_rule_id_in_workspace_1: str,
    ) -> None:
        """Test admin 2 getting an urgency rule created by admin 1.

        Parameters
        ----------
        access_token_admin_2
            Access token for the admin user in workspace 2.
        client
            Test client for the FastAPI application.
        existing_rule_id_in_workspace_1
            ID of an existing urgency rule in workspace 1.
        """

        response = client.get(
            f"/urgency-rules/{existing_rule_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_2}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @staticmethod
    def test_admin_2_edit_admin_1_ud_rule(
        access_token_admin_2: str,
        client: TestClient,
        existing_rule_id_in_workspace_1: str,
    ) -> None:
        """Test admin 2 editing an urgency rule created by admin 1.

        Parameters
        ----------
        access_token_admin_2
            Access token for the admin user in workspace 2.
        client
            Test client for the FastAPI application.
        existing_rule_id_in_workspace_1
            ID of an existing urgency rule in workspace 1.
        """

        response = client.put(
            f"/urgency-rules/{existing_rule_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_2}"},
            json={
                "urgency_rule_metadata": {},
                "urgency_rule_text": "user2 rule",
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @staticmethod
    def test_user2_delete_user1_ud_rule(
        access_token_admin_2: str,
        client: TestClient,
        existing_rule_id_in_workspace_1: str,
    ) -> None:
        """Test user 2 deleting an urgency rule created by user 1.

        Parameters
        ----------
        access_token_admin_2
            Access token for the admin user in workspace 2.
        client
            Test client for the FastAPI application.
        existing_rule_id_in_workspace_1
            ID of an existing urgency rule in workspace 1.
        """

        response = client.delete(
            f"/urgency-rules/{existing_rule_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_2}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_convert_record_to_schema() -> None:
    """Test converting a record to a schema."""

    _id = 1
    workspace_id = 123
    record = UrgencyRuleDB(
        created_datetime_utc=datetime.now(timezone.utc),
        updated_datetime_utc=datetime.now(timezone.utc),
        urgency_rule_id=_id,
        urgency_rule_metadata={"extra_field": "extra value"},
        urgency_rule_text="sample text",
        urgency_rule_vector=await async_fake_embedding(),
        workspace_id=workspace_id,
    )
    result = _convert_record_to_schema(urgency_rule_db=record)
    assert result.urgency_rule_id == _id
    assert result.workspace_id == workspace_id
    assert result.urgency_rule_text == "sample text"
    assert result.urgency_rule_metadata["extra_field"] == "extra value"
