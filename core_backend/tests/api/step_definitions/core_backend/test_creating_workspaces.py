"""This module contains scenarios for testing workspace creation."""

from typing import Any

import httpx
from fastapi import status
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from core_backend.app.config import DEFAULT_API_QUOTA, DEFAULT_CONTENT_QUOTA
from core_backend.app.users.schemas import UserRoles

# Define scenario(s).
scenarios("core_backend/creating_workspaces.feature")


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


# Scenario: If users create workspaces, they are added to those workspaces as admins
# iff the workspaces did not exist before
@when(
    "Zia creates workspace Zia",
    target_fixture="zia_create_workspace_response",
)
def zia_create_workspace(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Zia creates a workspace.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from creating the workspace.
    """

    zia_access_token = user_workspace_responses["zia"]["access_token"]
    create_response = client.post(
        "/workspace/",
        headers={"Authorization": f"Bearer {zia_access_token}"},
        json={"workspace_name": "Workspace_Zia"},
    )
    assert create_response.status_code == status.HTTP_200_OK
    return create_response


@then("Zia should be added as an admin to workspace Zia with the expected quotas")
def check_zia_create_response(zia_create_workspace_response: httpx.Response) -> None:
    """Check that Zia is added as an admin to workspace Zia with the expected quotas.

    Parameters
    ----------
    zia_create_workspace_response
        The response object from creating the workspace.
    """

    json_responses = zia_create_workspace_response.json()
    assert isinstance(json_responses, list) and len(json_responses) == 1
    json_response = json_responses[0]
    assert json_response["api_daily_quota"] == DEFAULT_API_QUOTA
    assert json_response["content_quota"] == DEFAULT_CONTENT_QUOTA
    assert json_response["workspace_name"] == "Workspace_Zia"


@then("Zia's default workspace should still be workspace Carlos")
def check_zia_default_workspace(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> None:
    """Check that Zia's default workspace is still workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    zia_access_token = user_workspace_responses["zia"]["access_token"]
    response = client.get(
        "/user/current-user", headers={"Authorization": f"Bearer {zia_access_token}"}
    )
    json_response = response.json()
    assert json_response["is_default_workspace"] == [True, False]
    assert json_response["user_workspaces"][0]["user_role"] == UserRoles.READ_ONLY
    assert json_response["user_workspaces"][0]["workspace_name"] == "Workspace_Carlos"
    assert json_response["user_workspaces"][1]["user_role"] == UserRoles.ADMIN
    assert json_response["user_workspaces"][1]["workspace_name"] == "Workspace_Zia"


@when(
    "Sid tries to create workspace Amir",
    target_fixture="sid_create_workspace_response",
)
def sid_create_workspace(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Sid tries to create a workspace.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from creating the workspace.
    """

    sid_access_token = user_workspace_responses["sid"]["access_token"]
    create_response = client.post(
        "/workspace/",
        headers={"Authorization": f"Bearer {sid_access_token}"},
        json={"workspace_name": "Workspace_Amir"},
    )
    assert create_response.status_code == status.HTTP_200_OK
    return create_response


@then("No new workspaces should be created by Sid")
def check_sid_create_response(sid_create_workspace_response: httpx.Response) -> None:
    """Check that no new workspaces are created by Sid.

    Parameters
    ----------
    sid_create_workspace_response
        The response object from creating the workspace.
    """

    json_response = sid_create_workspace_response.json()
    assert isinstance(json_response, list) and len(json_response) == 0


@then("Sid should still be a read-only user in workspace Amir")
def check_sid_role_in_workspace_Amir(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> None:
    """Check that no new workspaces are created by Sid.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    sid_access_token = user_workspace_responses["sid"]["access_token"]
    response = client.get(
        "/user/current-user", headers={"Authorization": f"Bearer {sid_access_token}"}
    )
    json_response = response.json()
    assert json_response["is_default_workspace"] == [True]
    assert json_response["user_workspaces"][0]["user_role"] == UserRoles.READ_ONLY
    assert json_response["user_workspaces"][0]["workspace_name"] == "Workspace_Amir"
