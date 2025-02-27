"""This module contains tests for the users API."""

import random
import string
from typing import Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.users.models import (
    UserAlreadyExistsError,
    UserNotFoundError,
    get_user_by_username,
    save_user_to_db,
)
from core_backend.app.users.schemas import UserCreate, UserRoles

from .conftest import (
    TEST_ADMIN_USERNAME_1,
    TEST_READ_ONLY_USERNAME_1,
    TEST_WORKSPACE_NAME_1,
)


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

        response = client.get(
            "/user/", headers={"Authorization": f"Bearer {access_token_admin_1}"}
        )

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

        response = client.get(
            "/user/", headers={"Authorization": f"Bearer {access_token_read_only_1}"}
        )
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

    def test_admin_1_create_user_in_workspace_1(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test that an admin in workspace 1 can create a new user in workspace 1.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        """

        response = client.post(
            "/user/",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "is_default_workspace": True,
                "password": "password",  # pragma: allowlist secret
                "role": UserRoles.READ_ONLY,
                "username": "mooooooooo",
                "workspace_name": TEST_WORKSPACE_NAME_1,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["is_default_workspace"] is True
        assert json_response["recovery_codes"]
        assert json_response["role"] == UserRoles.READ_ONLY
        assert json_response["username"] == "mooooooooo"
        assert json_response["workspace_name"] == TEST_WORKSPACE_NAME_1

    @pytest.mark.order(after="test_admin_1_create_user_in_workspace_1")
    def test_admin_1_create_user_in_workspace_1_with_existing_user(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test that an admin in workspace 1 cannot create a user with an existing
        username.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        """

        response = client.post(
            "/user/",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "is_default_workspace": True,
                "password": "password",  # pragma: allowlist secret
                "role": UserRoles.READ_ONLY,
                "username": "mooooooooo",
                "workspace_name": TEST_WORKSPACE_NAME_1,
            },
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
            headers={"Authorization": f"Bearer {access_token_read_only_1}"},
            json={
                "is_default_workspace": True,
                "password": "password",  # pragma: allowlist secret
                "role": UserRoles.ADMIN,
                "username": "test_username_6",
                "workspace_name": TEST_WORKSPACE_NAME_1,
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_1_create_admin_user_in_workspace_1(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test that an admin in workspace 1 can create a new admin user in workspace 1.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        """

        response = client.post(
            "/user/",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "is_default_workspace": True,
                "password": "password",  # pragma: allowlist secret
                "role": UserRoles.ADMIN,
                "username": "test_username_7",
                "workspace_name": TEST_WORKSPACE_NAME_1,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["is_default_workspace"] is True
        assert json_response["recovery_codes"]
        assert json_response["role"] == UserRoles.ADMIN
        assert json_response["username"] == "test_username_7"
        assert json_response["workspace_name"] == TEST_WORKSPACE_NAME_1


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
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "is_default_workspace": True,
                "username": admin_username,
                "workspace_name": TEST_WORKSPACE_NAME_1,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        response = client.get(
            "/user/current-user",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
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
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"username": username},
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.get(
            "/user/current-user",
            headers={"Authorization": f"Bearer {access_token_read_only_1}"},
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
            headers={"Authorization": f"Bearer {access_token_read_only_1}"},
            json={"username": "foobar"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUserPasswordReset:
    """Tests for the PUT /user/reset-password endpoint."""

    def test_admin_1_reset_own_password(
        self, admin_user_1_in_workspace_1: dict[str, Any], client: TestClient
    ) -> None:
        """Test that an admin user can reset their password.

        Parameters
        ----------
        admin_user_1_in_workspace_1
            Admin user in workspace 1.
        client
            Test client.
        """

        recovery_codes = admin_user_1_in_workspace_1["recovery_codes"]
        username = admin_user_1_in_workspace_1["username"]
        for code in recovery_codes:
            letters = string.ascii_letters
            random_string = "".join(random.choice(letters) for _ in range(8))
            response = client.put(
                "/user/reset-password",
                json={
                    "password": random_string,
                    "recovery_code": code,
                    "username": username,
                },
            )
            assert response.status_code == status.HTTP_200_OK

        response = client.put(
            "/user/reset-password",
            json={
                "password": "password",  # pragma: allowlist secret
                "recovery_code": recovery_codes[-1],
                "username": username,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_admin_user_reset_password(
        self, client: TestClient, read_only_user_1_in_workspace_1: dict[str, Any]
    ) -> None:
        """Test that a non-admin user is allowed to reset their password.

        Parameters
        ----------
        client
            Test client.
        read_only_user_1_in_workspace_1
            Read-only user in workspace 1.
        """

        recovery_codes = read_only_user_1_in_workspace_1["recovery_codes"]
        username = read_only_user_1_in_workspace_1["username"]
        response = client.put(
            "/user/reset-password",
            json={
                "password": "password",  # pragma: allowlist secret
                "recovery_code": recovery_codes[1],
                "username": username,
            },
        )

        assert response.status_code == status.HTTP_200_OK

    def test_reset_password_invalid_recovery_code(self, client: TestClient) -> None:
        """Test that an invalid recovery code is rejected.

        Parameters
        ----------
        client
            Test client.
        """

        response = client.put(
            "/user/reset-password",
            json={
                "password": "password",  # pragma: allowlist secret
                "recovery_code": "12345",
                "username": TEST_ADMIN_USERNAME_1,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reset_password_invalid_user(self, client: TestClient) -> None:
        """Test that an invalid user is rejected.

        Parameters
        ----------
        client
            Test client.
        """

        response = client.put(
            "/user/reset-password",
            json={
                "password": "password",  # pragma: allowlist secret
                "recovery_code": "1234",
                "username": "invalid_username",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUserFetching:
    """Tests for the GET /user/{user_id} endpoint."""

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
            "/user/current-user",
            headers={"Authorization": f"Bearer {access_token_read_only_1}"},
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


class TestUsers:
    """Tests for the users API."""

    async def test_save_user_to_db(self, asession: AsyncSession) -> None:
        """Test saving a user to the database.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        """

        user = UserCreate(
            is_default_workspace=True,
            role=UserRoles.READ_ONLY,
            username="test_username_3",
            workspace_name="test_workspace_3",
        )
        saved_user = await save_user_to_db(asession=asession, user=user)
        assert saved_user.username == "test_username_3"

    async def test_save_user_to_db_existing_user(self, asession: AsyncSession) -> None:
        """Test saving a user to the database when the user already exists.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        """

        user = UserCreate(
            is_default_workspace=True,
            role=UserRoles.READ_ONLY,
            username=TEST_READ_ONLY_USERNAME_1,
            workspace_name=TEST_WORKSPACE_NAME_1,
        )
        with pytest.raises(UserAlreadyExistsError):
            await save_user_to_db(asession=asession, user=user)

    async def test_get_user_by_username(self, asession: AsyncSession) -> None:
        """Test getting a user by their username.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        """

        retrieved_user = await get_user_by_username(
            asession=asession, username=TEST_READ_ONLY_USERNAME_1
        )
        assert retrieved_user.username == TEST_READ_ONLY_USERNAME_1

    async def test_get_user_by_username_no_user(self, asession: AsyncSession) -> None:
        """Test getting a user by their username when the user does not exist.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        """

        with pytest.raises(UserNotFoundError):
            await get_user_by_username(asession=asession, username="nonexistent")
