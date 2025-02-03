"""This module contains scenarios for testing the first user registration process."""

from typing import Any

import httpx
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from core_backend.app.users.schemas import UserRoles

# Define scenario(s).
scenarios("core_backend/users/first_user_registration.feature")


# Backgrounds.
@given("An empty database")
def reset_databases(clean_user_and_workspace_dbs: pytest.FixtureRequest) -> None:
    """Reset the `UserDB` and `WorkspaceDB` tables.

    Parameters
    ----------
    clean_user_and_workspace_dbs
        The fixture to clean the `UserDB` and `WorkspaceDB` tables.
    """

    pass


# Scenarios.
@when("I create Tony as the first user", target_fixture="create_tony_json_response")
def create_tony_as_first_user(client: TestClient) -> dict[str, Any]:
    """Create Tony as the first user.

    Parameters
    ----------
    client
        The test client for the FastAPI application.

    Returns
    -------
    dict[str, Any]
        The JSON response from creating Tony as the first user.
    """

    response = client.get("/user/require-register")
    json_response = response.json()
    assert json_response["require_register"] is True
    response = client.post(
        "/user/register-first-user",
        json={
            "password": "123",
            "role": UserRoles.ADMIN,
            "username": "Tony",
            "workspace_name": None,
        },
    )
    return response.json()


@then("The returned response should contain the expected values")
def check_first_user_return_response_is_successful(
    create_tony_json_response: dict[str, Any]
) -> None:
    """Check that the response from creating Tony contains the expected values.

    Parameters
    ----------
    create_tony_json_response
        The JSON response from creating Tony as the first user.
    """

    assert create_tony_json_response["is_default_workspace"] is True
    assert "password" not in create_tony_json_response
    assert len(create_tony_json_response["recovery_codes"]) > 0
    assert create_tony_json_response["role"] == UserRoles.ADMIN
    assert create_tony_json_response["username"] == "Tony"
    assert create_tony_json_response["workspace_name"] == "Workspace_Tony"


@then("I am able to authenticate as Tony", target_fixture="access_token_tony")
def authenticate_as_tony(client: TestClient) -> str:
    """Authenticate as Tony and check the authentication details.

    Parameters
    ----------
    client
        The test client for the FastAPI application.

    Returns
    -------
    str
        The access token for Tony.
    """

    response = client.post("/login", data={"username": "Tony", "password": "123"})
    json_response = response.json()

    assert json_response["access_level"] == "fullaccess"
    assert json_response["access_token"]
    assert json_response["username"] == "Tony"

    return json_response["access_token"]


@then("Tony belongs to the correct workspace with the correct role")
def verify_workspace_and_role_for_tony(
    access_token_tony: str, client: TestClient
) -> None:
    """Verify that the first user belongs to the correct workspace with the correct
    role.

    Parameters
    ----------
    access_token_tony
        The access token for Tony.
    client
        The test client for the FastAPI application.
    """

    response = client.get(
        "/user/", headers={"Authorization": f"Bearer {access_token_tony}"}
    )
    json_responses = response.json()
    assert len(json_responses) == 1
    json_response = json_responses[0]
    assert (
        len(json_response["is_default_workspace"]) == 1
        and json_response["is_default_workspace"][0] is True
    )
    assert json_response["username"] == "Tony"
    assert (
        len(json_response["user_workspace_names"]) == 1
        and json_response["user_workspace_names"][0] == "Workspace_Tony"
    )
    assert (
        len(json_response["user_workspace_roles"]) == 1
        and json_response["user_workspace_roles"][0] == UserRoles.ADMIN
    )


@when(
    "Tony tries to register Mark as a first user",
    target_fixture="register_mark_response",
)
def try_to_register_mark(client: TestClient) -> dict[str, Any]:
    """Try to register Mark as a user.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    """

    response = client.get("/user/require-register")
    assert response.json()["require_register"] is False
    register_mark_response = client.post(
        "/user/register-first-user",
        json={
            "password": "123",
            "role": UserRoles.READ_ONLY,
            "username": "Mark",
            "workspace_name": "Workspace_Tony",
        },
    )
    return register_mark_response


@then("Tony should not be allowed to register Mark as the first user")
def check_that_mark_is_not_allowed_to_register(
    client: TestClient, register_mark_response: httpx.Response
) -> None:
    """Check that Mark is not allowed to be registered as the first user.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    register_mark_response
        The response from trying to register Mark as a user.
    """

    assert register_mark_response.status_code == status.HTTP_400_BAD_REQUEST


@when(
    "Tony adds Mark as the second user with a read-only role",
    target_fixture="mark_response",
)
def add_mark_as_second_user(access_token_tony: str, client: TestClient) -> None:
    """Try to register Mark as a user.

    Parameters
    ----------
    access_token_tony
        The access token for Tony.
    client
        The test client for the FastAPI application.
    """

    response = client.post(
        "/user/",
        headers={"Authorization": f"Bearer {access_token_tony}"},
        json={
            "is_default_workspace": False,  # Check that this becomes true afterwards
            "password": "123",
            "role": UserRoles.READ_ONLY,
            "username": "Mark",
            "workspace_name": "Workspace_Tony",
        },
    )
    json_response = response.json()
    return json_response


@then("The returned response from adding Mark should contain the expected values")
def check_mark_return_response_is_successful(mark_response: dict[str, Any]) -> None:
    """Check that the response from adding Mark contains the expected values.

    Parameters
    ----------
    mark_response
        The JSON response from adding Mark as the second user.
    """

    assert mark_response["is_default_workspace"] is True
    assert mark_response["recovery_codes"]
    assert mark_response["role"] == UserRoles.READ_ONLY
    assert mark_response["username"] == "Mark"
    assert mark_response["workspace_name"] == "Workspace_Tony"


@then("Mark is able to authenticate himself")
def check_mark_authentication(client: TestClient) -> None:
    """Check that Mark is able to authenticate himself.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    """

    response = client.post("/login", data={"username": "Mark", "password": "123"})
    json_response = response.json()
    assert json_response["access_level"] == "fullaccess"
    assert json_response["access_token"]
    assert json_response["username"] == "Mark"
