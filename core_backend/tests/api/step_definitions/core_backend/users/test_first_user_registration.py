"""This module contains scenarios for testing the first user registration process."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from core_backend.app.users.schemas import UserRoles

# Define scenario(s).
scenarios("core_backend/users/first_user_registration.feature")


@given("there are no current users or workspaces")
def check_for_empty_databases(
    clean_user_and_workspace_dbs: pytest.FixtureRequest, client: TestClient
) -> None:
    """Check for empty `UserDB` and `WorkspaceDB` tables.

    NB: The `clean_user_and_workspace_dbs` fixture is used to clean the appropriate
    databases first; otherwise, we'll have existing records in tables from other tests.

    Parameters
    ----------
    clean_user_and_workspace_dbs
        The fixture to clean the `UserDB` and `WorkspaceDB` tables.
    client
        The test client for the FastAPI application.
    """

    response = client.get("/user/require-register")
    json_response = response.json()
    assert json_response["require_register"] is True


@given("a username and password for registration")
def provide_first_username_and_password(request: pytest.FixtureRequest) -> None:
    """Cache a username and password for registration.

    Parameters
    ----------
    request
        The pytest request object.
    """

    request.node.first_user_credentials = ("fru", "123")


@when("I call the endpoint to create the first user")
def create_the_first_user(client: TestClient, request: pytest.FixtureRequest) -> None:
    """Create the first user.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    request
        The pytest request object.
    """

    username, password = request.node.first_user_credentials
    response = client.post(
        "/user/register-first-user",
        json={
            "password": password,
            "role": UserRoles.ADMIN,
            "username": username,
            "workspace_name": None,
        },
    )
    request.node.first_user_json_response = response.json()


@then("the returned response should contain the expected values")
def check_first_user_response_is_successful(
    request: pytest.FixtureRequest,
) -> None:
    """Check that the response from creating the first user contains the expected
    values.

    Parameters
    ----------
    request
        The pytest request object.
    """

    username, password = request.node.first_user_credentials
    workspace_name = f"Workspace_{username}"
    json_response = request.node.first_user_json_response
    assert json_response["is_default_workspace"] is True
    assert "password" not in json_response
    assert len(json_response["recovery_codes"]) > 0
    assert json_response["role"] == UserRoles.ADMIN
    assert json_response["username"] == username
    assert json_response["workspace_name"] == workspace_name


@then("I am able to authenticate as the first user")
def sign_in_as_first_user(client: TestClient, request: pytest.FixtureRequest) -> None:
    """Sign in as the first user and check the authentication details.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    request
        The pytest request object.
    """

    username, password = request.node.first_user_credentials
    response = client.post("/login", data={"username": username, "password": password})
    json_response = response.json()
    assert json_response["access_level"] == "fullaccess"
    assert json_response["access_token"]
    assert json_response["username"] == username
    request.node.first_user_access_token = json_response["access_token"]


@then("the first user belongs to the correct workspace with the correct role")
def verify_first_user_workspace_and_role(
    client: TestClient, request: pytest.FixtureRequest
) -> None:
    """Verify that the first user belongs to the correct workspace with the correct
    role.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    request
        The pytest request object.
    """

    username, password = request.node.first_user_credentials
    access_token = request.node.first_user_access_token
    response = client.get("/user/", headers={"Authorization": f"Bearer {access_token}"})
    json_responses = response.json()
    assert len(json_responses) == 1
    json_response = json_responses[0]
    assert (
        len(json_response["is_default_workspace"]) == 1
        and json_response["is_default_workspace"][0] is True
    )
    assert json_response["username"] == username
    assert (
        len(json_response["user_workspace_names"]) == 1
        and json_response["user_workspace_names"][0] == f"Workspace_{username}"
    )
    assert (
        len(json_response["user_workspace_roles"]) == 1
        and json_response["user_workspace_roles"][0] == UserRoles.ADMIN
    )
