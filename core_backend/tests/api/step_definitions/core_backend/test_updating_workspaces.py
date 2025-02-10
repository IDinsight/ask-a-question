"""This module contains scenarios for testing updating workspaces."""

from typing import Any

import httpx
from fastapi import status
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from core_backend.app.config import DEFAULT_API_QUOTA, DEFAULT_CONTENT_QUOTA

# Define scenario(s).
scenarios("core_backend/updating_workspaces.feature")


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


# Scenario: Admin users updating workspaces
@when(
    "Poornima updates the name and quotas for workspace Amir",
    target_fixture="poornima_update_workspace_response",
)
def poornima_update_workspace(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Poornima updates the name and quotas for workspace Amir.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from the update workspace request.
    """

    poornima_access_token = user_workspace_responses["poornima"]["access_token"]
    poornima_workspace_id = user_workspace_responses["poornima"][
        "workspace_name_to_id"
    ]["Workspace_Amir"]
    create_response = client.put(
        f"/workspace/{poornima_workspace_id}",
        headers={"Authorization": f"Bearer {poornima_access_token}"},
        json={
            "api_daily_quota": None,
            "content_quota": None,
            "workspace_name": "Workspace_Amir_Updated",
        },
    )
    assert create_response.status_code == status.HTTP_200_OK
    return create_response


@then("The name for workspace Amir should be updated but not the quotas")
def check_poornima_update_response(
    client: TestClient, poornima_update_workspace_response: httpx.Response
) -> None:
    """Check that the name for workspace Amir should be updated to workspace
    Amir_Updated but the quotas are not updated.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    poornima_update_workspace_response
        The response object from the update workspace request.
    """

    json_response = poornima_update_workspace_response.json()
    assert json_response["api_daily_quota"] == DEFAULT_API_QUOTA
    assert json_response["content_quota"] == DEFAULT_CONTENT_QUOTA
    assert json_response["workspace_name"] == "Workspace_Amir_Updated"


# Scenario: Non-admin users updating workspaces
@when(
    "Zia updates the name and quotas for workspace Carlos",
    target_fixture="zia_update_workspace_response",
)
def zia_update_workspace(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Zia updates the name and quotas for workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from the update workspace request.
    """

    zia_access_token = user_workspace_responses["zia"]["access_token"]
    zia_workspace_id = user_workspace_responses["zia"]["workspace_name_to_id"][
        "Workspace_Carlos"
    ]
    create_response = client.put(
        f"/workspace/{zia_workspace_id}",
        headers={"Authorization": f"Bearer {zia_access_token}"},
        json={
            "api_daily_quota": None,
            "content_quota": None,
            "workspace_name": "Workspace_Carlos_Updated",
        },
    )
    return create_response


@then("Zia should get an error")
def check_zia_update_response(
    client: TestClient, zia_update_workspace_response: httpx.Response
) -> None:
    """Check that Zia should get an error.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    zia_update_workspace_response
        The response object from the update workspace request.
    """

    assert zia_update_workspace_response.status_code == status.HTTP_403_FORBIDDEN
