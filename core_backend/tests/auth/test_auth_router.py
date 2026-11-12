"""This module contains tests for the authentication API (`/login`,
`/login-google`) and the bearer-token dependencies shared by other routers.
"""

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.auth import service
from app.core.security import create_access_token
from app.users.schemas import UserRoles
from tests.conftest import (
    TEST_ADMIN_USERNAME_1,
    TEST_WORKSPACE_NAME_1,
    TEST_WORKSPACE_NAME_2,
)

LOGIN_PASSWORD = "login_password"  # pragma: allowlist secret


@pytest.fixture
def login_user(access_token_admin_1: str, client: TestClient) -> dict[str, Any]:
    """Create a fresh read-only user in workspace 1 with a known password.

    A dedicated user is used so password changes made by other tests to the
    session-wide users cannot break these logins.

    Parameters
    ----------
    access_token_admin_1
        Admin access token in workspace 1.
    client
        Test client.

    Returns
    -------
    dict[str, Any]
        The `/user/` response body.
    """

    response = client.post(
        "/user/",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
        json={
            "password": LOGIN_PASSWORD,
            "role": UserRoles.READ_ONLY,
            "username": f"login_user_{uuid.uuid4().hex[:8]}",
            "workspace_name": TEST_WORKSPACE_NAME_1,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()


@pytest.fixture
def fake_google(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace Google ID-token verification so no network call is made.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    MagicMock
        The fake `verify_oauth2_token`; set its `return_value` / `side_effect`.
    """

    verify = MagicMock()
    monkeypatch.setattr(
        service, "id_token", SimpleNamespace(verify_oauth2_token=verify)
    )
    return verify


class TestLogin:
    """Tests for the POST /login endpoint."""

    def test_login(self, client: TestClient, login_user: dict[str, Any]) -> None:
        """Test that valid credentials return a bearer token for the default
        workspace, and that the token can be used on protected endpoints.

        Parameters
        ----------
        client
            Test client.
        login_user
            A fresh user with a known password.
        """

        response = client.post(
            "/login",
            data={"password": LOGIN_PASSWORD, "username": login_user["username"]},
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["access_level"] == "fullaccess"
        assert body["token_type"] == "bearer"
        assert body["user_role"] == UserRoles.READ_ONLY
        assert body["username"] == login_user["username"]
        assert body["workspace_name"] == TEST_WORKSPACE_NAME_1

        response = client.get(
            "/user/current-user",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["username"] == login_user["username"]

    @pytest.mark.parametrize("username", ["login_user", "no_such_user"])
    def test_login_invalid_credentials(
        self, client: TestClient, login_user: dict[str, Any], username: str
    ) -> None:
        """Test that a wrong password or unknown user returns 401.

        Parameters
        ----------
        client
            Test client.
        login_user
            A fresh user with a known password.
        username
            `login_user` to use the fresh user, otherwise a literal username.
        """

        if username == "login_user":
            username = login_user["username"]
        response = client.post(
            "/login", data={"password": "wrong_password", "username": username}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_fields(self, client: TestClient) -> None:
        """Test that the OAuth2 form fields are required.

        Parameters
        ----------
        client
            Test client.
        """

        response = client.post("/login", data={"username": "only_username"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestLoginGoogle:
    """Tests for the POST /login-google endpoint."""

    def test_new_then_returning_google_user(
        self, client: TestClient, fake_google: MagicMock
    ) -> None:
        """Test that a first Google sign-in creates the user and their workspace,
        and that a second sign-in logs into the same workspace.

        Parameters
        ----------
        client
            Test client.
        fake_google
            Fake Google token verifier.
        """

        gmail = f"google_{uuid.uuid4().hex[:8]}@gmail.com"
        fake_google.return_value = {"email": gmail, "iss": "accounts.google.com"}
        payload = {"client_id": "client", "credential": "google-token"}

        for _ in range(2):  # First call registers, second authenticates.
            response = client.post("/login-google", json=payload)
            assert response.status_code == status.HTTP_200_OK
            body = response.json()
            assert body["username"] == gmail
            assert body["user_role"] == UserRoles.ADMIN
            assert body["workspace_name"] == f"{gmail}'s Workspace"

    def test_invalid_google_token(
        self, client: TestClient, fake_google: MagicMock
    ) -> None:
        """Test that a token rejected by Google returns 401.

        Parameters
        ----------
        client
            Test client.
        fake_google
            Fake Google token verifier.
        """

        fake_google.side_effect = ValueError("Token expired")
        response = client.post(
            "/login-google", json={"client_id": "client", "credential": "bad"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_credential(self, client: TestClient) -> None:
        """Test that the Google credential is required.

        Parameters
        ----------
        client
            Test client.
        """

        response = client.post("/login-google", json={"client_id": "client"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestAuthenticateKeyDependency:
    """Tests for the `authenticate_key` dependency (used e.g. by `/search`)."""

    @pytest.mark.parametrize(
        "headers",
        [{}, {"Authorization": "Bearer neither-api-key-nor-jwt"}],
        ids=["no-token", "invalid-token"],
    )
    def test_rejects_bad_tokens(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        """Test that requests without a valid API key or JWT are rejected.

        Parameters
        ----------
        client
            Test client.
        headers
            Request headers.
        """

        response = client.post("/search", headers=headers, json={"query_text": "hi"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# Placeholder resolved to the `login_user` fixture's username inside the test.
FRESH_USER = "<fresh user in workspace 1>"


class TestTokenMembershipChecks:
    """A signed JWT is only honoured while its user still exists and still belongs
    to the workspace in the token. These hit routes that used to trust the token's
    `workspace_name` claim alone (read-only content routes and the JWT fallback of
    `authenticate_key`).
    """

    @staticmethod
    def _bearer(username: str, workspace_name: str) -> dict[str, str]:
        """Build an Authorization header with a correctly signed token.

        Parameters
        ----------
        username
            The `username` claim.
        workspace_name
            The `workspace_name` claim.

        Returns
        -------
        dict[str, str]
            The headers.
        """

        token = create_access_token(
            user_role=UserRoles.ADMIN, username=username, workspace_name=workspace_name
        )
        return {"Authorization": f"Bearer {token}"}

    def test_member_is_allowed(self, client: TestClient) -> None:
        """Positive control: admin 1 can read workspace 1 content.

        Parameters
        ----------
        client
            Test client.
        """

        headers = self._bearer(TEST_ADMIN_USERNAME_1, TEST_WORKSPACE_NAME_1)
        assert client.get("/content/", headers=headers).status_code == 200

    @pytest.mark.parametrize(
        "username, workspace_name",
        [
            # User was deleted (or never existed) but the token is still signed.
            ("ghost_user_" + uuid.uuid4().hex, TEST_WORKSPACE_NAME_1),
            # Real user (fresh, only in workspace 1), but the token names workspace 2.
            (FRESH_USER, TEST_WORKSPACE_NAME_2),
            # Workspace does not exist.
            (TEST_ADMIN_USERNAME_1, "no_such_workspace_" + uuid.uuid4().hex),
        ],
        ids=["user-gone", "not-a-member", "workspace-gone"],
    )
    @pytest.mark.parametrize(
        "method, path, body",
        [
            ("GET", "/content/", None),
            ("GET", "/tag/", None),
            ("GET", "/urgency-rules/", None),
            ("GET", "/workspace/current-workspace", None),
            ("POST", "/search", {"query_text": "hi"}),
        ],
        ids=["content", "tags", "urgency-rules", "current-workspace", "search"],
    )
    def test_non_member_is_rejected(
        self,
        body: dict[str, Any] | None,
        client: TestClient,
        method: str,
        path: str,
        request: pytest.FixtureRequest,
        username: str,
        workspace_name: str,
    ) -> None:
        """Signed tokens for non-members are rejected with 401.

        Parameters
        ----------
        body
            JSON body to send, if any.
        client
            Test client.
        method
            HTTP method.
        path
            Route to call.
        request
            Pytest request, used to create the fresh user only when needed.
        username
            The `username` claim (`FRESH_USER` = a new user in workspace 1 only).
        workspace_name
            The `workspace_name` claim.
        """

        if username == FRESH_USER:
            username = request.getfixturevalue("login_user")["username"]
        response = client.request(
            method, path, headers=self._bearer(username, workspace_name), json=body
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestNoSecretsInResponses:
    """User-facing responses never include password hashes or recovery codes."""

    def test_current_user(self, access_token_admin_1: str, client: TestClient) -> None:
        """`/user/current-user` exposes no credential material.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        """

        response = client.get(
            "/user/current-user",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "hashed_password" not in response.text
        assert "recovery_code" not in response.text
        assert "$argon2" not in response.text


class TestRefreshAndLogout:
    """Tests for POST /refresh and POST /logout against the real Redis."""

    @pytest.fixture
    def tokens(self, client: TestClient, login_user: dict[str, Any]) -> dict[str, Any]:
        """Log the fresh user in.

        Parameters
        ----------
        client
            Test client.
        login_user
            A fresh user with a known password.

        Returns
        -------
        dict[str, Any]
            The /login response body.
        """

        response = client.post(
            "/login",
            data={"password": LOGIN_PASSWORD, "username": login_user["username"]},
        )
        assert response.status_code == status.HTTP_200_OK
        return response.json()

    def test_refresh_issues_working_tokens(
        self, client: TestClient, tokens: dict[str, Any]
    ) -> None:
        """Test that /refresh returns a new pair whose access token works and whose
        old refresh token no longer does.

        Parameters
        ----------
        client
            Test client.
        tokens
            The /login response body.
        """

        assert tokens["refresh_token"]
        assert tokens["expires_in"] > 0

        response = client.post(
            "/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == status.HTTP_200_OK
        refreshed = response.json()
        assert refreshed["refresh_token"] != tokens["refresh_token"]
        assert refreshed["workspace_name"] == TEST_WORKSPACE_NAME_1

        response = client.get(
            "/user/current-user",
            headers={"Authorization": f"Bearer {refreshed['access_token']}"},
        )
        assert response.status_code == status.HTTP_200_OK

        # Reuse of the rotated-out token is rejected and revokes the new one too.
        response = client.post(
            "/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response = client.post(
            "/refresh", json={"refresh_token": refreshed["refresh_token"]}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_revokes_refresh_token(
        self, client: TestClient, tokens: dict[str, Any]
    ) -> None:
        """Test that /logout returns 204 and the refresh token stops working.

        Parameters
        ----------
        client
            Test client.
        tokens
            The /login response body.
        """

        response = client.post(
            "/logout", json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        response = client.post(
            "/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_token_is_not_a_refresh_token(
        self, client: TestClient, tokens: dict[str, Any]
    ) -> None:
        """Test that an access token is rejected by /refresh.

        Parameters
        ----------
        client
            Test client.
        tokens
            The /login response body.
        """

        response = client.post(
            "/refresh", json={"refresh_token": tokens["access_token"]}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_switch_workspace_issues_refresh_token(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test that switching workspace returns a refresh token for the new
        workspace that can be exchanged.

        Parameters
        ----------
        access_token_admin_1
            Admin access token in workspace 1.
        client
            Test client.
        """

        response = client.post(
            "/workspace/switch-workspace",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"workspace_name": TEST_WORKSPACE_NAME_1},
        )
        assert response.status_code == status.HTTP_200_OK
        response = client.post(
            "/refresh", json={"refresh_token": response.json()["refresh_token"]}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["workspace_name"] == TEST_WORKSPACE_NAME_1
