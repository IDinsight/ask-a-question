"""This module contains scenarios for testing creating/adding users to workspaces."""

from typing import Any
from unittest.mock import patch

import httpx
from fastapi import status
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from core_backend.app.users.schemas import UserRoles

# Define scenario(s).
scenarios("core_backend/google_user_sign_in.feature")


# Backgrounds.
@given("Multiple workspaces are setup", target_fixture="user_workspace_responses")
def reset_databases(
    setup_multiple_workspaces: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Setup multiple workspaces.

    Parameters
    ----------
    setup_multiple_workspaces
        The fixture for setting up multiple workspaces.

    Returns
    -------
    dict[str, dict[str, Any]]
        A dictionary containing the response objects for the different users.
    """

    return setup_multiple_workspaces


# Scenario: Wamuyu authenticates using her gmail
@when(
    "Wamuyu signs in using her gmail",
    target_fixture="wamuyu_google_create_response",
)
def wamuyu_signs_in_using_gmail(client: TestClient) -> httpx.Response:
    """Wamuyu signs in using her gmail.

    Parameters
    ----------
    client
        The test client for the FastAPI application.

    Returns
    -------
    httpx.Response
        The response object from Wamuyu signing in using her gmail.
    """

    mock_id_token_response = {"iss": "accounts.google.com", "email": "wamuyu@gmail.com"}
    login_data = {"client_id": "fake-client-id", "credential": "fake-credential"}

    with patch(
        "core_backend.app.auth.routers.id_token.verify_oauth2_token",
        return_value=mock_id_token_response,
    ):
        create_response = client.post("/login-google", json=login_data)
    assert create_response.status_code == status.HTTP_200_OK

    return create_response


@then("Wamuyu should be added to Wamuyu's Workspace")
def check_wamuyu_create_response(wamuyu_google_create_response: httpx.Response) -> None:
    """Check that Wamuyu was added to Wamuyu's Workspace.

    Parameters
    ----------
    wamuyu_google_create_response
        The response object from Wamuyu signing in using her gmail.
    """

    json_response = wamuyu_google_create_response.json()
    assert json_response["access_level"] == "fullaccess"
    assert json_response["access_token"]
    assert json_response["token_type"] == "bearer"
    assert json_response["user_role"] == UserRoles.ADMIN
    assert json_response["username"] == "wamuyu@gmail.com"
    assert json_response["workspace_name"] == "wamuyu@gmail.com's Workspace"


@then("Wamuyu should be able to sign into her workspace again")
def wamuyu_signs_in_again(client: TestClient) -> None:
    """Wamuyu signs in again using her gmail.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    """

    mock_id_token_response = {"iss": "accounts.google.com", "email": "wamuyu@gmail.com"}
    login_data = {"client_id": "fake-client-id", "credential": "fake-credential"}

    with patch(
        "core_backend.app.auth.routers.id_token.verify_oauth2_token",
        return_value=mock_id_token_response,
    ):
        sign_in_again_response = client.post("/login-google", json=login_data)
    json_response = sign_in_again_response.json()
    assert json_response["access_level"] == "fullaccess"
    assert json_response["access_token"]
    assert json_response["token_type"] == "bearer"
    assert json_response["user_role"] == UserRoles.ADMIN
    assert json_response["username"] == "wamuyu@gmail.com"
    assert json_response["workspace_name"] == "wamuyu@gmail.com's Workspace"


@when(
    "Zia creates to create a workspace called wamuyu@gmail.com's Workspace",
    target_fixture="zia_create_response",
)
def zia_create_wamuyu_gmail_workspace(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Zia tries creates to create a workspace called "wamuyu@gmail.com".

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from Zia creating a workspace.
    """

    zia_access_token = user_workspace_responses["zia"]["access_token"]
    create_response = client.post(
        "/workspace/",
        headers={"Authorization": f"Bearer {zia_access_token}"},
        json={"workspace_name": "wamuyu@gmail.com's Workspace"},
    )

    return create_response


@then("Zia should receive an empty list as a response")
def check_zia_create_response(zia_create_response: httpx.Response) -> None:
    """Check that Zia received an empty list as a response.

    Parameters
    ----------
    zia_create_response
        The response object from Zia creating a workspace.
    """

    assert zia_create_response.status_code == status.HTTP_200_OK
    json_response = zia_create_response.json()
    assert json_response == []


# Scenario: Zia creates wamuyu@gmail.com's Workspace
@when(
    "Zia creates wamuyu@gmail.com's Workspace first",
    target_fixture="zia_create_first_response",
)
def zia_create_wamuyu_gmail_workspace_first(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Zia creates Wamuyu's gmail workspace first.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from Zia creating Wamuyu's gmail workspace first.
    """

    zia_access_token = user_workspace_responses["zia"]["access_token"]
    create_response = client.post(
        "/workspace/",
        headers={"Authorization": f"Bearer {zia_access_token}"},
        json={"workspace_name": "wamuyu@gmail.com's Workspace"},
    )

    return create_response


@then("Zia should be able to create Wamuyu's gmail workspace")
def check_zia_create_first_response(zia_create_first_response: httpx.Response) -> None:
    """Check that Zia received an empty list as a response.

    Parameters
    ----------
    zia_create_first_response
        The response object from Zia creating Wamuyu's gmail workspace first.
    """

    assert zia_create_first_response.status_code == status.HTTP_200_OK
    json_response = zia_create_first_response.json()
    assert json_response[0]["workspace_name"] == "wamuyu@gmail.com's Workspace"


@when(
    "Wamuyu tries to sign in using her gmail",
    target_fixture="wamuyu_google_sign_in_response",
)
def wamuyu_tries_to_sign_in_using_gmail(client: TestClient) -> httpx.Response:
    """Wamuyu tries to sign in using her gmail.

    Parameters
    ----------
    client
        The test client for the FastAPI application.

    Returns
    -------
    httpx.Response
        The response object from Wamuyu trying to sign in using her gmail.
    """

    mock_id_token_response = {"iss": "accounts.google.com", "email": "wamuyu@gmail.com"}
    login_data = {"client_id": "fake-client-id", "credential": "fake-credential"}

    with patch(
        "core_backend.app.auth.routers.id_token.verify_oauth2_token",
        return_value=mock_id_token_response,
    ):
        create_response = client.post("/login-google", json=login_data)

    return create_response


@then("Wamuyu should get an error")
def check_wamuyu_create_second_response(
    wamuyu_google_sign_in_response: httpx.Response,
) -> None:
    """Check that Wamuyu got an error.

    Parameters
    ----------
    wamuyu_google_sign_in_response
        The response object from Wamuyu trying to sign in using her gmail.
    """

    assert wamuyu_google_sign_in_response.status_code == status.HTTP_400_BAD_REQUEST
