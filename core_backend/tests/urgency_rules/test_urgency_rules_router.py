"""This module contains tests for urgency rules endpoints."""

# pylint: disable=W0621
from typing import Generator

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.exceptions import AppError

VALID_RULE = {"urgency_rule_metadata": {}, "urgency_rule_text": "valid rule"}


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


class TestUrgencyRulesAuthAndValidation:
    """Tests for authentication, authorisation and request validation."""

    @pytest.mark.parametrize(
        "method, path",
        [
            ("post", "/urgency-rules/"),
            ("get", "/urgency-rules/"),
            ("get", "/urgency-rules/1"),
            ("put", "/urgency-rules/1"),
            ("delete", "/urgency-rules/1"),
        ],
    )
    def test_missing_token(self, client: TestClient, method: str, path: str) -> None:
        """Every endpoint requires a user token.

        Parameters
        ----------
        client
            Test client for the FastAPI application.
        method
            The HTTP method.
        path
            The endpoint path.
        """

        response = client.request(method, path, json=VALID_RULE)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "method, path",
        [
            ("post", "/urgency-rules/"),
            ("put", "/urgency-rules/12345"),
            ("delete", "/urgency-rules/12345"),
        ],
    )
    def test_read_only_user_cannot_modify(
        self,
        access_token_read_only_1: str,
        client: TestClient,
        method: str,
        path: str,
    ) -> None:
        """Only workspace admins may create, update or delete rules.

        The role check runs before the rule lookup, so a non-existent ID still
        returns 403 rather than 404.

        Parameters
        ----------
        access_token_read_only_1
            Access token for the read-only user in workspace 1.
        client
            Test client for the FastAPI application.
        method
            The HTTP method.
        path
            The endpoint path.
        """

        response = client.request(
            method,
            path,
            headers={"Authorization": f"Bearer {access_token_read_only_1}"},
            json=VALID_RULE,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "method, path, body",
        [
            ("post", "/urgency-rules/", {"urgency_rule_metadata": {}}),
            ("post", "/urgency-rules/", {"urgency_rule_text": "x" * 256}),
            ("put", "/urgency-rules/1", {"urgency_rule_text": None}),
            ("get", "/urgency-rules/not-an-int", None),
        ],
        ids=["missing_text", "text_too_long", "null_text", "non_int_id"],
    )
    def test_invalid_request(
        self,
        access_token_admin_1: str,
        body: dict | None,
        client: TestClient,
        method: str,
        path: str,
    ) -> None:
        """Malformed bodies and path parameters fail validation.

        Parameters
        ----------
        access_token_admin_1
            Access token for the admin user in workspace 1.
        body
            The request body.
        client
            Test client for the FastAPI application.
        method
            The HTTP method.
        path
            The endpoint path.
        """

        response = client.request(
            method,
            path,
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json=body,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.parametrize("method", ["get", "delete"])
    def test_rule_not_found(
        self, access_token_admin_1: str, client: TestClient, method: str
    ) -> None:
        """Getting or deleting an unknown rule returns 404.

        Parameters
        ----------
        access_token_admin_1
            Access token for the admin user in workspace 1.
        client
            Test client for the FastAPI application.
        method
            The HTTP method.
        """

        response = client.request(
            method,
            "/urgency-rules/12345",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Urgency Rule ID `12345` not found"}

    @pytest.mark.parametrize(
        "method, path, service_name",
        [
            ("post", "/urgency-rules/", "create_urgency_rule"),
            ("put", "/urgency-rules/1", "update_urgency_rule"),
        ],
    )
    def test_embedding_failure_returns_502(
        self,
        access_token_admin_1: str,
        client: TestClient,
        method: str,
        monkeypatch: pytest.MonkeyPatch,
        path: str,
        service_name: str,
    ) -> None:
        """A 502 raised by the service reaches the client unchanged.

        Parameters
        ----------
        access_token_admin_1
            Access token for the admin user in workspace 1.
        client
            Test client for the FastAPI application.
        method
            The HTTP method.
        monkeypatch
            Pytest monkeypatch fixture.
        path
            The endpoint path.
        service_name
            The service function the endpoint calls.
        """

        async def fail(**kwargs: object) -> None:
            """Raise the error the service raises when embedding fails.

            Parameters
            ----------
            kwargs
                Ignored service arguments.

            Raises
            ------
            AppError
                Always, with status 502.
            """

            raise AppError("embedding down", status_code=status.HTTP_502_BAD_GATEWAY)

        monkeypatch.setattr(f"app.urgency_rules.router.service.{service_name}", fail)

        response = client.request(
            method,
            path,
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json=VALID_RULE,
        )
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert response.json() == {"detail": "embedding down"}
