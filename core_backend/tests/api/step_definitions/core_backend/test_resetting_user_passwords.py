"""This module contains scenarios for testing resetting user passwords."""

from typing import Any

import httpx
from fastapi import status
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

# Define scenario(s).
scenarios("core_backend/resetting_user_passwords.feature")


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


# Scenarios.
@when(
    "Suzin tries to reset her own password",
    target_fixture="suzin_reset_password_response",
)
def suzin_reset_own_password(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Suzin resets her own password.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Suzin resetting her own password.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    suzin_recovery_codes = user_workspace_responses["suzin"]["recovery_codes"]
    reset_password_response = client.put(
        "/user/reset-password",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={
            "password": "456",
            "recovery_code": suzin_recovery_codes[0],
            "username": "Suzin",
        },
    )
    return reset_password_response


@then("Suzin should be able to reset her own password")
def check_suzin_reset_password_response(
    client: TestClient, suzin_reset_password_response: httpx.Response
) -> None:
    """Check that Suzin can reset her own password.

    Parameters
    ----------
    client
        Test client for the FastAPI application.
    suzin_reset_password_response
        The response from Suzin resetting her own password.
    """

    assert suzin_reset_password_response.status_code == status.HTTP_200_OK
    json_response = suzin_reset_password_response.json()
    assert json_response["is_default_workspace"] == [True, False, False]
    assert json_response["user_workspaces"] == [
        {"user_role": "admin", "workspace_id": 1, "workspace_name": "Workspace_Suzin"},
        {"user_role": "admin", "workspace_id": 2, "workspace_name": "Workspace_Carlos"},
        {"user_role": "admin", "workspace_id": 3, "workspace_name": "Workspace_Amir"},
    ]
    assert json_response["username"] == "Suzin"

    suzin_login_response = client.post(
        "/login", data={"username": "Suzin", "password": "456"}
    )
    assert suzin_login_response.status_code == status.HTTP_200_OK


@when(
    "Suzin tries to reset Mark's password",
    target_fixture="suzin_reset_mark_password_response",
)
def suzin_reset_mark_password(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Suzin resets Mark's password.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Suzin resetting Mark's password.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    mark_recovery_codes = user_workspace_responses["mark"]["recovery_codes"]
    reset_password_response = client.put(
        "/user/reset-password",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={
            "password": "456",
            "recovery_code": mark_recovery_codes[0],
            "username": "Mark",
        },
    )
    return reset_password_response


@then("Suzin gets an error")
def check_suzin_reset_password_responses(
    suzin_reset_mark_password_response: httpx.Response,
) -> None:
    """Check that Suzin cannot reset Mark's password.

    Parameters
    ----------
    suzin_reset_mark_password_response
        The response from Suzin resetting Mark's password.
    """

    assert suzin_reset_mark_password_response.status_code == status.HTTP_403_FORBIDDEN


@when(
    "Mark tries to reset Suzin's password",
    target_fixture="mark_reset_suzin_password_response",
)
def mark_reset_suzin_password(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Mark resets Suzin's password.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Mark resetting Suzin's password.
    """

    mark_access_token = user_workspace_responses["mark"]["access_token"]
    suzin_recovery_codes = user_workspace_responses["suzin"]["recovery_codes"]
    reset_password_response = client.put(
        "/user/reset-password",
        headers={"Authorization": f"Bearer {mark_access_token}"},
        json={
            "password": "123",
            "recovery_code": suzin_recovery_codes[1],
            "username": "Suzin",
        },
    )
    return reset_password_response


@then("Mark gets an error")
def check_mark_reset_suzin_password_responses(
    mark_reset_suzin_password_response: httpx.Response,
) -> None:
    """Check that Mark cannot reset Suzin's password.

    Parameters
    ----------
    mark_reset_suzin_password_response
        The response from Mark resetting Suzin's password.
    """

    assert mark_reset_suzin_password_response.status_code == status.HTTP_403_FORBIDDEN


@when(
    "Poornima tries to reset Suzin's password",
    target_fixture="poornima_reset_suzin_password_response",
)
def poornima_reset_suzin_password(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Poornima resets Suzin's password.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Poornima resetting Suzin's password.
    """

    poornima_access_token = user_workspace_responses["poornima"]["access_token"]
    suzin_recovery_codes = user_workspace_responses["suzin"]["recovery_codes"]
    reset_password_response = client.put(
        "/user/reset-password",
        headers={"Authorization": f"Bearer {poornima_access_token}"},
        json={
            "password": "123",
            "recovery_code": suzin_recovery_codes[1],
            "username": "Suzin",
        },
    )
    return reset_password_response


@then("Poornima gets an error")
def check_poornima_reset_suzin_password_responses(
    poornima_reset_suzin_password_response: httpx.Response,
) -> None:
    """Check that Mark cannot reset Suzin's password.

    Parameters
    ----------
    poornima_reset_suzin_password_response
        The response from Poornima resetting Suzin's password.
    """

    assert (
        poornima_reset_suzin_password_response.status_code == status.HTTP_403_FORBIDDEN
    )
