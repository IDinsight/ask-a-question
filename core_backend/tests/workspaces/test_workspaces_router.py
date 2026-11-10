"""This module contains tests for the workspaces API.

Tests that rename a workspace or rotate an API key use the `temp_workspace`
fixture, so the shared workspaces (and the session-scoped API keys other features'
tests depend on) are never changed and no test ordering is needed.
"""

from typing import Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import DEFAULT_API_QUOTA, DEFAULT_CONTENT_QUOTA
from app.users.schemas import UserRoles
from tests.conftest import TEST_WORKSPACE_NAME_1, TEST_WORKSPACE_NAME_2
from tests.workspaces.conftest import unique_name


def auth(token: str) -> dict[str, str]:
    """Build the bearer authorization header.

    Parameters
    ----------
    token
        The access token.

    Returns
    -------
    dict[str, str]
        The request headers.
    """

    return {"Authorization": f"Bearer {token}"}


class TestAuthAndValidation:
    """Requests rejected before reaching the service layer."""

    @pytest.mark.parametrize(
        "method, path",
        [
            ("post", "/workspace/"),
            ("get", "/workspace/"),
            ("get", "/workspace/current-workspace"),
            ("get", "/workspace/1"),
            ("get", "/workspace/get-user-workspaces/1"),
            ("put", "/workspace/rotate-key"),
            ("post", "/workspace/switch-workspace"),
            ("put", "/workspace/1"),
        ],
    )
    def test_requires_token(self, client: TestClient, method: str, path: str) -> None:
        """Test that every workspace endpoint returns 401 without a bearer token.

        Parameters
        ----------
        client
            Test client.
        method
            HTTP method.
        path
            Request path.
        """

        response = client.request(method, path)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "method, path, body",
        [
            ("post", "/workspace/", {"doc_language": "ENGLISH"}),
            ("post", "/workspace/switch-workspace", {}),
            ("get", "/workspace/not-an-int", None),
            ("put", "/workspace/1", {"api_daily_quota": "lots"}),
        ],
    )
    def test_validation_errors(
        self,
        access_token_admin_1: str,
        body: dict[str, Any] | None,
        client: TestClient,
        method: str,
        path: str,
    ) -> None:
        """Test that invalid payloads and parameters return 422.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        body
            JSON request body.
        client
            Test client.
        method
            HTTP method.
        path
            Request path.
        """

        response = client.request(
            method, path, headers=auth(access_token_admin_1), json=body
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestCreateWorkspaces:
    """Tests for the POST /workspace/ endpoint."""

    def test_create_single_and_list(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test creating one workspace and then a list containing it again.

        Quotas in the request are ignored in favour of the global defaults, and an
        existing workspace is silently left out of the response.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        """

        first, second = unique_name("create_a"), unique_name("create_b")
        response = client.post(
            "/workspace/",
            headers=auth(access_token_admin_1),
            json={"api_daily_quota": 1, "content_quota": 1, "workspace_name": first},
        )
        assert response.status_code == status.HTTP_200_OK
        (created,) = response.json()
        assert created["workspace_name"] == first
        assert created["api_daily_quota"] == DEFAULT_API_QUOTA
        assert created["content_quota"] == DEFAULT_CONTENT_QUOTA

        response = client.post(
            "/workspace/",
            headers=auth(access_token_admin_1),
            json=[{"workspace_name": first}, {"workspace_name": second}],
        )
        assert response.status_code == status.HTTP_200_OK
        assert [w["workspace_name"] for w in response.json()] == [second]


class TestRetrieveWorkspaces:
    """Tests for the GET /workspace/... endpoints."""

    def test_retrieve_all_workspaces(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test that an admin gets the workspaces they administer.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        """

        response = client.get("/workspace/", headers=auth(access_token_admin_1))
        assert response.status_code == status.HTTP_200_OK
        names = {w["workspace_name"] for w in response.json()}
        assert {TEST_WORKSPACE_NAME_1, TEST_WORKSPACE_NAME_2} <= names

    def test_read_only_cannot_list_workspaces(
        self, access_token_read_only_1: str, client: TestClient
    ) -> None:
        """Test that a user who is not an admin anywhere gets 403.

        Parameters
        ----------
        access_token_read_only_1
            Read-only user access token in workspace 1.
        client
            Test client.
        """

        response = client.get("/workspace/", headers=auth(access_token_read_only_1))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_current_workspace(
        self, access_token_read_only_1: str, client: TestClient
    ) -> None:
        """Test that any authenticated user can read their current workspace.

        Parameters
        ----------
        access_token_read_only_1
            Read-only user access token in workspace 1.
        client
            Test client.
        """

        response = client.get(
            "/workspace/current-workspace", headers=auth(access_token_read_only_1)
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["workspace_name"] == TEST_WORKSPACE_NAME_1

    @pytest.mark.parametrize(
        "token_fixture, expected_status",
        [
            ("access_token_admin_1", status.HTTP_200_OK),
            ("access_token_admin_2", status.HTTP_403_FORBIDDEN),
        ],
    )
    def test_retrieve_workspace_by_id(
        self,
        client: TestClient,
        expected_status: int,
        request: pytest.FixtureRequest,
        token_fixture: str,
        workspace_1_id: int,
    ) -> None:
        """Test that only admins of a workspace can read it by ID.

        Parameters
        ----------
        client
            Test client.
        expected_status
            Expected HTTP status code.
        request
            Pytest request object, used to resolve the token fixture by name.
        token_fixture
            Name of the access-token fixture to call with.
        workspace_1_id
            ID of workspace 1.
        """

        token = request.getfixturevalue(token_fixture)
        response = client.get(f"/workspace/{workspace_1_id}", headers=auth(token))
        assert response.status_code == expected_status
        if expected_status == status.HTTP_200_OK:
            assert response.json()["workspace_name"] == TEST_WORKSPACE_NAME_1

    @pytest.mark.parametrize(
        "token_fixture, user, expected_status",
        [
            ("access_token_admin_1", "read_only_1", status.HTTP_200_OK),
            ("access_token_admin_2", "read_only_1", status.HTTP_403_FORBIDDEN),
            ("access_token_admin_1", "unknown", status.HTTP_404_NOT_FOUND),
        ],
    )
    def test_retrieve_workspaces_by_user_id(
        self,
        access_token_read_only_1: str,
        client: TestClient,
        expected_status: int,
        request: pytest.FixtureRequest,
        token_fixture: str,
        user: str,
    ) -> None:
        """Test listing another user's workspaces.

        Parameters
        ----------
        access_token_read_only_1
            Read-only user access token in workspace 1 (used to find its user ID).
        client
            Test client.
        expected_status
            Expected HTTP status code.
        request
            Pytest request object, used to resolve the token fixture by name.
        token_fixture
            Name of the access-token fixture to call with.
        user
            Which user to look up: read-only user 1, or an unknown ID.
        """

        if user == "unknown":
            user_id = -1
        else:
            # A read-only user listing users only gets themselves back.
            (me,) = client.get("/user/", headers=auth(access_token_read_only_1)).json()
            user_id = me["user_id"]

        token = request.getfixturevalue(token_fixture)
        response = client.get(
            f"/workspace/get-user-workspaces/{user_id}", headers=auth(token)
        )
        assert response.status_code == expected_status
        if expected_status == status.HTTP_200_OK:
            names = [w["workspace_name"] for w in response.json()]
            assert names == [TEST_WORKSPACE_NAME_1]


class TestWorkspaceKeyManagement:
    """Tests for the PUT /workspace/rotate-key endpoint."""

    def test_rotate_key_invalidates_old_key(
        self, client: TestClient, temp_workspace: dict[str, Any]
    ) -> None:
        """Test that a rotated key works and the previous key stops working.

        Parameters
        ----------
        client
            Test client.
        temp_workspace
            A fresh workspace administered by admin 1.
        """

        def rotate() -> str:
            response = client.put(
                "/workspace/rotate-key", headers=auth(temp_workspace["access_token"])
            )
            assert response.status_code == status.HTTP_200_OK
            body = response.json()
            assert body["workspace_name"] == temp_workspace["workspace_name"]
            return body["new_api_key"]

        def search(api_key: str) -> int:
            return client.post(
                "/search",
                headers=auth(api_key),
                json={"query_text": "Tell me about a good sport to play"},
            ).status_code

        first_api_key = rotate()
        assert search(first_api_key) == status.HTTP_200_OK

        second_api_key = rotate()
        assert second_api_key != first_api_key
        assert search(second_api_key) == status.HTTP_200_OK
        assert search(first_api_key) == status.HTTP_401_UNAUTHORIZED

    def test_read_only_cannot_rotate_key(
        self, access_token_read_only_1: str, client: TestClient
    ) -> None:
        """Test that a read-only user cannot rotate the workspace key.

        Parameters
        ----------
        access_token_read_only_1
            Read-only user access token in workspace 1.
        client
            Test client.
        """

        response = client.put(
            "/workspace/rotate-key", headers=auth(access_token_read_only_1)
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestSwitchWorkspace:
    """Tests for the POST /workspace/switch-workspace endpoint."""

    @pytest.mark.parametrize(
        "workspace_name, expected_status",
        [
            (TEST_WORKSPACE_NAME_2, status.HTTP_200_OK),
            ("no_such_workspace", status.HTTP_400_BAD_REQUEST),
        ],
    )
    def test_switch_workspace(
        self,
        access_token_admin_1: str,
        client: TestClient,
        expected_status: int,
        workspace_name: str,
    ) -> None:
        """Test switching to a workspace the user belongs to, and to one they don't.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        expected_status
            Expected HTTP status code.
        workspace_name
            The workspace to switch into.
        """

        response = client.post(
            "/workspace/switch-workspace",
            headers=auth(access_token_admin_1),
            json={"workspace_name": workspace_name},
        )
        assert response.status_code == expected_status
        if expected_status == status.HTTP_200_OK:
            body = response.json()
            assert body["workspace_name"] == workspace_name
            assert body["user_role"] == UserRoles.ADMIN
            assert body["token_type"] == "bearer"
            assert body["access_token"]


class TestUpdateWorkspace:
    """Tests for the PUT /workspace/{workspace_id} endpoint."""

    def test_update_workspace_with_allowed_changes(
        self, client: TestClient, temp_workspace: dict[str, Any]
    ) -> None:
        """Test that workspace can be updated with allowed changes.

        Parameters
        ----------
        client
            Test client.
        temp_workspace
            A fresh workspace administered by admin 1.
        """

        new_name = unique_name("renamed")
        response = client.put(
            f"/workspace/{temp_workspace['workspace_id']}",
            headers=auth(temp_workspace["access_token"]),
            json={"doc_language": "FRENCH", "workspace_name": new_name},
        )
        assert response.status_code == status.HTTP_200_OK

        response_json = response.json()
        assert response_json["doc_language"] == "FRENCH"
        assert response_json["workspace_name"] == new_name

    def test_update_workspace_with_no_changes(
        self, client: TestClient, temp_workspace: dict[str, Any]
    ) -> None:
        """Test that workspace can be updated even though nothing is changed.

        Parameters
        ----------
        client
            Test client.
        temp_workspace
            A fresh workspace administered by admin 1.
        """

        response = client.put(
            f"/workspace/{temp_workspace['workspace_id']}",
            headers=auth(temp_workspace["access_token"]),
            json={
                "doc_language": "ENGLISH",
                "workspace_name": temp_workspace["workspace_name"],
            },
        )
        assert response.status_code == status.HTTP_200_OK

        response_json = response.json()
        # Quotas cannot be changed through this endpoint.
        assert response_json["api_daily_quota"] == temp_workspace["api_daily_quota"]
        assert response_json["content_quota"] == temp_workspace["content_quota"]
        assert response_json["doc_language"] == "ENGLISH"
        assert response_json["workspace_name"] == temp_workspace["workspace_name"]

    def test_update_workspace_with_non_existing_workspace_fails(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test that updating a non-existing workspace fails.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin 1 in workspace 1.
        client
            Test client.
        """

        response = client.put(
            "/workspace/-1",
            headers=auth(access_token_admin_1),
            json={"doc_language": "ENGLISH", "workspace_name": TEST_WORKSPACE_NAME_1},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_workspace_using_existing_workspace_name_fails(
        self, client: TestClient, temp_workspace: dict[str, Any]
    ) -> None:
        """Test that updating a workspace name to an existing workspace name fails.

        Parameters
        ----------
        client
            Test client.
        temp_workspace
            A fresh workspace administered by admin 1.
        """

        response = client.put(
            f"/workspace/{temp_workspace['workspace_id']}",
            headers=auth(temp_workspace["access_token"]),
            json={"doc_language": "ENGLISH", "workspace_name": TEST_WORKSPACE_NAME_2},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_admin_cannot_update(
        self, access_token_admin_2: str, client: TestClient, workspace_1_id: int
    ) -> None:
        """Test that an admin of another workspace cannot update workspace 1.

        Parameters
        ----------
        access_token_admin_2
            Admin access token in workspace 2 (not a member of workspace 1).
        client
            Test client.
        workspace_1_id
            ID of workspace 1.
        """

        response = client.put(
            f"/workspace/{workspace_1_id}",
            headers=auth(access_token_admin_2),
            json={"doc_language": "FRENCH"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
