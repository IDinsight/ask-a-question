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


# Scenario: Users can only reset their own passwords
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

    suzin_recovery_codes = user_workspace_responses["suzin"]["recovery_codes"]
    reset_password_response = client.put(
        "/user/reset-password",
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
    for x, y in zip(
        json_response["is_default_workspace"], json_response["user_workspaces"]
    ):
        if x is True:
            assert y == {
                "user_role": "admin",
                "workspace_id": 1,
                "workspace_name": "Workspace_Suzin",
            }
        else:
            assert y in [
                {
                    "user_role": "admin",
                    "workspace_id": 2,
                    "workspace_name": "Workspace_Carlos",
                },
                {
                    "user_role": "admin",
                    "workspace_id": 3,
                    "workspace_name": "Workspace_Amir",
                },
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

    mark_recovery_codes = user_workspace_responses["mark"]["recovery_codes"]
    reset_password_response = client.put(
        "/user/reset-password",
        json={
            "password": "456",
            "recovery_code": mark_recovery_codes[0],
            "username": "Mark",
        },
    )
    return reset_password_response


@then("Suzin should be able to reset Mark's password")
def check_suzin_reset_mark_password_response(
    suzin_reset_mark_password_response: httpx.Response,
) -> None:
    """Check that Suzin can reset Mark's password.

    Parameters
    ----------
    suzin_reset_mark_password_response
        The response from Suzin resetting Mark's password.
    """

    assert suzin_reset_mark_password_response.status_code == status.HTTP_200_OK


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

    suzin_recovery_codes = user_workspace_responses["suzin"]["recovery_codes"]
    reset_password_response = client.put(
        "/user/reset-password",
        json={
            "password": "123",
            "recovery_code": suzin_recovery_codes[1],
            "username": "Suzin",
        },
    )
    return reset_password_response


@then("Mark should be able to reset Suzin's password")
def check_mark_reset_suzin_password_response(
    mark_reset_suzin_password_response: httpx.Response,
) -> None:
    """Check that Mark can reset Suzin's password.

    Parameters
    ----------
    mark_reset_suzin_password_response
        The response from Mark resetting Suzin's password.
    """

    assert mark_reset_suzin_password_response.status_code == status.HTTP_200_OK


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

    suzin_recovery_codes = user_workspace_responses["suzin"]["recovery_codes"]
    reset_password_response = client.put(
        "/user/reset-password",
        json={
            "password": "123",
            "recovery_code": suzin_recovery_codes[2],
            "username": "Suzin",
        },
    )
    return reset_password_response


@then("Poornima should be able to reset Suzin's password")
def check_poornima_reset_suzin_password_response(
    poornima_reset_suzin_password_response: httpx.Response,
) -> None:
    """Check that Poornima can reset Suzin's password.

    Parameters
    ----------
    poornima_reset_suzin_password_response
        The response from Poornima resetting Suzin's password.
    """

    assert poornima_reset_suzin_password_response.status_code == status.HTTP_200_OK
