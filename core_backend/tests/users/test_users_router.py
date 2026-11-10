"""This module contains tests for the users API."""

from typing import Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.repository import get_user_by_username
from app.users.schemas import UserRoles
from tests.conftest import (
    TEST_ADMIN_USERNAME_1,
    TEST_READ_ONLY_USERNAME_1,
    TEST_WORKSPACE_NAME_1,
)
from tests.users.conftest import NEW_USER_PASSWORD, unique_name


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
            ("get", "/user/"),
            ("get", "/user/current-user"),
            ("put", "/user/1"),
            ("delete", "/user/1?remove_from_workspace_name=x"),
            ("head", "/user/someone"),
        ],
    )
    def test_requires_token(self, client: TestClient, method: str, path: str) -> None:
        """Test that protected endpoints return 401 without a bearer token.

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

    def test_invalid_token(self, client: TestClient) -> None:
        """Test that a malformed JWT is rejected with 401.

        Parameters
        ----------
        client
            Test client.
        """

        response = client.get("/user/current-user", headers=auth("not-a-jwt"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.parametrize(
        "method, path, body",
        [
            ("post", "/user/", {"username": "no_password"}),
            ("put", "/user/reset-password", {"username": "x"}),
            ("delete", "/user/1", None),  # Missing `remove_from_workspace_name`.
            ("put", "/user/not-an-int", {"username": "x"}),
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


class TestGetAllUsers:
    """Tests for the GET /user/ endpoint."""

    def test_get_all_users_in_current_workspace(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test that an admin can get all users in the current workspace.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        """

        response = client.get("/user/", headers=auth(access_token_admin_1))

        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert len(json_response) > 0
        assert len(json_response[0]["is_default_workspace"]) == len(
            json_response[0]["user_workspaces"]
        )

    def test_get_all_users_non_admin_in_current_workspace(
        self, access_token_read_only_1: str, client: TestClient
    ) -> None:
        """Test that a non-admin user can just get themselves in the current workspace.

        Parameters
        ----------
        access_token_read_only_1
            Read-only user access token in workspace 1.
        client
            Test client.
        """

        response = client.get("/user/", headers=auth(access_token_read_only_1))
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert len(json_response) == 1
        assert (
            len(json_response[0]["is_default_workspace"])
            == len(json_response[0]["user_workspaces"])
            == 1
        )
        assert json_response[0]["is_default_workspace"][0] is True
        assert (
            json_response[0]["user_workspaces"][0]["user_role"] == UserRoles.READ_ONLY
        )
        assert json_response[0]["username"] == TEST_READ_ONLY_USERNAME_1


class TestUserCreation:
    """Tests for the POST /user/ endpoint."""

    @pytest.mark.parametrize("role", [UserRoles.READ_ONLY, UserRoles.ADMIN])
    def test_admin_1_create_user_in_workspace_1(
        self, access_token_admin_1: str, client: TestClient, role: UserRoles
    ) -> None:
        """Test that an admin in workspace 1 can create read-only and admin users in
        workspace 1, and that the same username cannot be created twice.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        role
            Role of the new user.
        """

        username = unique_name("created")
        payload = {
            "is_default_workspace": True,
            "password": "password",  # pragma: allowlist secret
            "role": role,
            "username": username,
            "workspace_name": TEST_WORKSPACE_NAME_1,
        }

        response = client.post(
            "/user/", headers=auth(access_token_admin_1), json=payload
        )

        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["is_default_workspace"] is True
        assert json_response["recovery_codes"]
        assert json_response["role"] == role
        assert json_response["username"] == username
        assert json_response["workspace_name"] == TEST_WORKSPACE_NAME_1

        # Creating the same username again is rejected.
        response = client.post(
            "/user/", headers=auth(access_token_admin_1), json=payload
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_admin_create_user_in_workspace_1(
        self, access_token_read_only_1: str, client: TestClient
    ) -> None:
        """Test that a non-admin user in workspace 1 cannot create a new user in
        workspace 1.

        Parameters
        ----------
        access_token_read_only_1
            Read-only user access token in workspace 1.
        client
            Test client.
        """

        response = client.post(
            "/user/",
            headers=auth(access_token_read_only_1),
            json={
                "is_default_workspace": True,
                "password": "password",  # pragma: allowlist secret
                "role": UserRoles.ADMIN,
                "username": "test_username_6",
                "workspace_name": TEST_WORKSPACE_NAME_1,
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAddExistingUser:
    """Tests for the POST /user/add-existing-user-to-workspace endpoint."""

    def test_add_existing_user_to_new_workspace(
        self,
        access_token_admin_1: str,
        client: TestClient,
        new_user_in_workspace_1: dict[str, Any],
    ) -> None:
        """Test adding an existing user to another workspace, then adding them again.

        A fresh workspace is used so the shared test workspaces are not modified.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        new_user_in_workspace_1
            A freshly created read-only user in workspace 1.
        """

        workspace_name = unique_name("add_existing_ws")
        response = client.post(
            "/workspace/",
            headers=auth(access_token_admin_1),
            json={"workspace_name": workspace_name},
        )
        assert response.status_code == status.HTTP_200_OK

        payload = {
            "role": UserRoles.READ_ONLY,
            "username": new_user_in_workspace_1["username"],
            "workspace_name": workspace_name,
        }
        response = client.post(
            "/user/add-existing-user-to-workspace",
            headers=auth(access_token_admin_1),
            json=payload,
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["is_default_workspace"] is False
        assert json_response["workspace_name"] == workspace_name

        # The user already has a role in that workspace.
        response = client.post(
            "/user/add-existing-user-to-workspace",
            headers=auth(access_token_admin_1),
            json=payload,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_unknown_user(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test that adding a user who does not exist returns 404.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        """

        response = client.post(
            "/user/add-existing-user-to-workspace",
            headers=auth(access_token_admin_1),
            json={"username": "no_such_user", "workspace_name": TEST_WORKSPACE_NAME_1},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestRegistration:
    """Tests for first-user registration endpoints.

    The session fixtures have already registered users, so registration is closed.
    """

    def test_require_register(self, client: TestClient) -> None:
        """Test that registration is not required once users exist.

        Parameters
        ----------
        client
            Test client.
        """

        response = client.get("/user/require-register")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"require_register": False}

    def test_register_first_user_when_users_exist(self, client: TestClient) -> None:
        """Test that a second "first user" cannot be registered.

        Parameters
        ----------
        client
            Test client.
        """

        response = client.post(
            "/user/register-first-user",
            json={"password": NEW_USER_PASSWORD, "username": unique_name("first")},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUserUpdate:
    """Tests for the PUT /user/{user_id} endpoint."""

    async def test_admin_1_update_admin_1_in_workspace_1(
        self,
        access_token_admin_1: str,
        admin_user_1_in_workspace_1: dict[str, Any],
        asession: AsyncSession,
        client: TestClient,
    ) -> None:
        """Test that an admin in workspace 1 can update themselves in workspace 1.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        admin_user_1_in_workspace_1
            Admin user in workspace 1.
        asession
            The SQLAlchemy async session to use for all database connections.
        client
            Test client.
        """

        admin_user_db = await get_user_by_username(
            asession=asession, username=admin_user_1_in_workspace_1["username"]
        )
        admin_username = admin_user_db.username
        admin_user_id = admin_user_db.user_id
        response = client.put(
            f"/user/{admin_user_id}",
            headers=auth(access_token_admin_1),
            json={
                "is_default_workspace": True,
                "username": admin_username,
                "workspace_name": TEST_WORKSPACE_NAME_1,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        response = client.get("/user/current-user", headers=auth(access_token_admin_1))
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        for i, uw_dict in enumerate(json_response["user_workspaces"]):
            if uw_dict["workspace_name"] == TEST_WORKSPACE_NAME_1:
                assert json_response["is_default_workspace"][i] is True
                break
        assert json_response["username"] == admin_username

    async def test_admin_1_update_other_user_in_workspace_1(
        self,
        access_token_admin_1: str,
        access_token_read_only_1: str,
        asession: AsyncSession,
        client: TestClient,
        read_only_user_1_in_workspace_1: dict[str, Any],
    ) -> None:
        """Test that an admin in workspace 1 can update another user in workspace 1.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        access_token_read_only_1
            Read-only user access token in workspace 1.
        asession
            The SQLAlchemy async session to use for all database connections.
        client
            Test client.
        read_only_user_1_in_workspace_1
            Read-only user in workspace 1.
        """

        user_db = await get_user_by_username(
            asession=asession, username=read_only_user_1_in_workspace_1["username"]
        )
        username = user_db.username
        user_id = user_db.user_id
        response = client.put(
            f"/user/{user_id}",
            headers=auth(access_token_admin_1),
            json={"username": username},
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.get(
            "/user/current-user", headers=auth(access_token_read_only_1)
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["username"] == username

    @pytest.mark.parametrize("is_same_user", [True, False])
    async def test_non_admin_update_admin_1_in_workspace_1(
        self,
        access_token_read_only_1: str,
        admin_user_1_in_workspace_1: dict[str, Any],
        asession: AsyncSession,
        client: TestClient,
        is_same_user: bool,
        read_only_user_1_in_workspace_1: dict[str, Any],
    ) -> None:
        """Test that a non-admin user in workspace 1 cannot update an admin user or
        themselves in workspace 1.

        Parameters
        ----------
        access_token_read_only_1
            Read-only user access token in workspace 1.
        admin_user_1_in_workspace_1
            Admin user in workspace 1.
        asession
            The SQLAlchemy async session to use for all database connections.
        client
            Test client.
        is_same_user
            Specifies whether the user being updated is the same as the user making the
            request.
        read_only_user_1_in_workspace_1
            Read-only user in workspace 1.
        """

        admin_user_db = await get_user_by_username(
            asession=asession, username=admin_user_1_in_workspace_1["username"]
        )
        admin_user_id = admin_user_db.user_id

        user_db_1 = await get_user_by_username(
            asession=asession, username=read_only_user_1_in_workspace_1["username"]
        )
        user_id_1 = user_db_1.user_id

        user_id = admin_user_id if is_same_user else user_id_1
        response = client.put(
            f"/user/{user_id}",
            headers=auth(access_token_read_only_1),
            json={"username": "foobar"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_role_without_workspace(
        self,
        access_token_admin_1: str,
        client: TestClient,
        new_user_in_workspace_1: dict[str, Any],
    ) -> None:
        """Test that changing a role without naming the workspace returns 400.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        new_user_in_workspace_1
            A freshly created read-only user in workspace 1.
        """

        response = client.put(
            f"/user/{new_user_in_workspace_1['user_id']}",
            headers=auth(access_token_admin_1),
            json={
                "role": UserRoles.ADMIN,
                "username": new_user_in_workspace_1["username"],
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUserPasswordReset:
    """Tests for the PUT /user/reset-password endpoint.

    A fresh user is used so the session-wide users keep their passwords and
    recovery codes.
    """

    def test_reset_own_password(
        self, client: TestClient, new_user_in_workspace_1: dict[str, Any]
    ) -> None:
        """Test that a user can reset their password and that each recovery code
        can only be used once.

        Parameters
        ----------
        client
            Test client.
        new_user_in_workspace_1
            A freshly created read-only user in workspace 1.
        """

        payload = {
            "password": "another_password",  # pragma: allowlist secret
            "recovery_code": new_user_in_workspace_1["recovery_codes"][0],
            "username": new_user_in_workspace_1["username"],
        }
        response = client.put("/user/reset-password", json=payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["username"] == new_user_in_workspace_1["username"]

        # The same recovery code cannot be used twice.
        response = client.put("/user/reset-password", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize(
        "username, expected_status",
        [
            (TEST_ADMIN_USERNAME_1, status.HTTP_400_BAD_REQUEST),  # Wrong code.
            ("invalid_username", status.HTTP_404_NOT_FOUND),
        ],
    )
    def test_reset_password_rejected(
        self, client: TestClient, expected_status: int, username: str
    ) -> None:
        """Test that an invalid recovery code or unknown user is rejected.

        Parameters
        ----------
        client
            Test client.
        expected_status
            Expected HTTP status code.
        username
            Username in the request.
        """

        response = client.put(
            "/user/reset-password",
            json={
                "password": "password",  # pragma: allowlist secret
                "recovery_code": "12345",
                "username": username,
            },
        )

        assert response.status_code == expected_status


class TestUserFetching:
    """Tests for the GET /user/current-user and HEAD /user/{username} endpoints."""

    def test_get_user(self, access_token_read_only_1: str, client: TestClient) -> None:
        """Test that a user can get their own information and that the correct
        information is retrieved.

        Parameters
        ----------
        access_token_read_only_1
            Read-only user access token in workspace 1.
        client
            Test client.
        """

        response = client.get(
            "/user/current-user", headers=auth(access_token_read_only_1)
        )
        assert response.status_code == status.HTTP_200_OK

        json_response = response.json()
        expected_keys = [
            "created_datetime_utc",
            "is_default_workspace",
            "updated_datetime_utc",
            "username",
            "user_id",
            "user_workspaces",
        ]
        for key in expected_keys:
            assert key in json_response, f"Missing key: {key}"

    @pytest.mark.parametrize(
        "token_fixture, username, expected_status",
        [
            ("access_token_admin_1", TEST_READ_ONLY_USERNAME_1, status.HTTP_200_OK),
            ("access_token_admin_1", "no_such_user", status.HTTP_404_NOT_FOUND),
            (
                "access_token_read_only_1",
                TEST_ADMIN_USERNAME_1,
                status.HTTP_403_FORBIDDEN,
            ),
        ],
    )
    def test_check_if_username_exists(
        self,
        client: TestClient,
        expected_status: int,
        request: pytest.FixtureRequest,
        token_fixture: str,
        username: str,
    ) -> None:
        """Test the HEAD username check for admins and non-admins.

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
        username
            Username to look up.
        """

        token = request.getfixturevalue(token_fixture)
        response = client.head(f"/user/{username}", headers=auth(token))
        assert response.status_code == expected_status


class TestUserRemoval:
    """Tests for the DELETE /user/{user_id} endpoint."""

    def test_admin_removes_user_from_only_workspace(
        self,
        access_token_admin_1: str,
        client: TestClient,
        new_user_in_workspace_1: dict[str, Any],
    ) -> None:
        """Test that removing a user from their only workspace deletes them.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        new_user_in_workspace_1
            A freshly created read-only user in workspace 1.
        """

        response = client.delete(
            f"/user/{new_user_in_workspace_1['user_id']}",
            headers=auth(access_token_admin_1),
            params={"remove_from_workspace_name": TEST_WORKSPACE_NAME_1},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "default_workspace_name": None,
            "removed_from_workspace_name": TEST_WORKSPACE_NAME_1,
            "require_authentication": False,
            "require_workspace_switch": False,
        }

        # The user no longer exists.
        response = client.head(
            f"/user/{new_user_in_workspace_1['username']}",
            headers=auth(access_token_admin_1),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize(
        "workspace_name, expected_status",
        [
            (TEST_WORKSPACE_NAME_1, status.HTTP_403_FORBIDDEN),  # Not an admin.
            ("no_such_workspace", status.HTTP_400_BAD_REQUEST),
        ],
    )
    def test_remove_rejected(
        self,
        access_token_read_only_1: str,
        client: TestClient,
        expected_status: int,
        new_user_in_workspace_1: dict[str, Any],
        workspace_name: str,
    ) -> None:
        """Test that non-admins and unknown workspaces are rejected.

        Parameters
        ----------
        access_token_read_only_1
            Read-only user access token in workspace 1.
        client
            Test client.
        expected_status
            Expected HTTP status code.
        new_user_in_workspace_1
            A freshly created read-only user in workspace 1.
        workspace_name
            Workspace to remove the user from.
        """

        response = client.delete(
            f"/user/{new_user_in_workspace_1['user_id']}",
            headers=auth(access_token_read_only_1),
            params={"remove_from_workspace_name": workspace_name},
        )
        assert response.status_code == expected_status
