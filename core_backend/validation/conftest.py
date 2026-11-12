"""Fixtures shared by the validation suites (`retrieval/`, `urgency_detection/`).

The suites run against a freshly migrated, empty database. This conftest sets up
the workspace they run in through the public API, the same way a new deployment is
set up, so it keeps working as the internal models change:

1. POST /user/register-first-user creates an admin user and their workspace.
2. POST /login gives an access token for that workspace.
3. PUT /workspace/rotate-key gives the workspace API key used by /search and
   /urgency-detect.

The password is random per run and never leaves this process.
"""

import secrets
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_sqlalchemy_async_engine
from app.main import app

VALIDATION_USERNAME = "validation_admin"


@dataclass(frozen=True)
class ValidationWorkspace:
    """Credentials for the workspace the validation suites run in."""

    access_token: str
    api_key: str
    workspace_name: str


def _check(response_status: int, step: str, body: str) -> None:
    """Fail the run with a readable message if a setup call did not succeed.

    Parameters
    ----------
    response_status
        The HTTP status code returned.
    step
        What the call was doing, for the error message.
    body
        The response body, for the error message.

    Raises
    ------
    RuntimeError
        If the status is not 200.
    """

    if response_status != 200:
        raise RuntimeError(
            f"Validation setup failed to {step} (HTTP {response_status}): {body}"
        )


@pytest.fixture(scope="session")
def validation_workspace() -> ValidationWorkspace:
    """Create the validation workspace and return its credentials.

    The setup client is closed (app lifespan shut down) before this returns, so a
    suite's own client, which depends on this fixture, starts a clean lifespan.

    Returns
    -------
    ValidationWorkspace
        The admin access token, workspace API key and workspace name.

    Raises
    ------
    RuntimeError
        If the database already has users (the suites need an empty database), or
        any setup call fails.
    """

    password = secrets.token_urlsafe(24)

    with TestClient(app) as client:
        response = client.get("/user/require-register")
        _check(response.status_code, "check the database is empty", response.text)
        if not response.json()["require_register"]:
            raise RuntimeError(
                "Validation needs an empty, freshly migrated database, but users "
                "already exist. Recreate the database and run "
                "`alembic upgrade head`."
            )

        # 1.
        response = client.post(
            "/user/register-first-user",
            json={"password": password, "username": VALIDATION_USERNAME},
        )
        _check(response.status_code, "register the first user", response.text)

        # 2.
        response = client.post(
            "/login", data={"password": password, "username": VALIDATION_USERNAME}
        )
        _check(response.status_code, "log in", response.text)
        login = response.json()

        # 3.
        response = client.put(
            "/workspace/rotate-key",
            headers={"Authorization": f"Bearer {login['access_token']}"},
        )
        _check(response.status_code, "create the workspace API key", response.text)
        api_key = response.json()["new_api_key"]

        # asyncpg connections belong to the event loop that opened them, and the
        # app's async engine is global. Close the pooled ones on this client's loop
        # so the suite's own client (another loop) opens fresh connections.
        if client.portal is None:  # Only unset when the client is closed.
            raise RuntimeError("Validation setup client closed unexpectedly.")
        client.portal.call(get_sqlalchemy_async_engine().dispose)

    return ValidationWorkspace(
        access_token=login["access_token"],
        api_key=api_key,
        workspace_name=login["workspace_name"],
    )
