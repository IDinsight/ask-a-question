"""This module contains scenarios for testing users switching between multiple
workspaces.
"""

from typing import Any

import httpx
from fastapi import status
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

# Define scenario(s).
scenarios("core_backend/switching_workspaces.feature")


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


@when(
    "Suzin switches to Workspace Carlos and Workspace Amir",
    target_fixture="suzin_switch_workspaces_response",
)
def suzin_switches_workspaces(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> dict[str, httpx.Response]:
    """Suzin switches to Workspace Carlos and Workspace Amir.

    NB: Suzin is all powerful since she is the OG admin and created workspace for
    everyone. Thus, Suzin should be able to switch to any workspace, unless an admin of
    that workspace removes her.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    dict[str, httpx.Response]
        The responses from switching to Workspace Carlos and Workspace Amir.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    switch_to_workspace_carlos_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={"workspace_name": "Workspace_Carlos"},
    )
    switch_to_workspace_amir_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={"workspace_name": "Workspace_Amir"},
    )
    return {
        "switch_to_workspace_carlos_response": switch_to_workspace_carlos_response,
        "switch_to_workspace_amir_response": switch_to_workspace_amir_response,
    }


@then("Suzin should be able to switch to both workspaces")
def check_suzin_workspace_switch_responses(
    suzin_switch_workspaces_response: dict[str, httpx.Response],
    user_workspace_responses: dict[str, dict[str, Any]],
) -> None:
    """Check that Suzin can switch to both workspaces.

    Parameters
    ----------
    suzin_switch_workspaces_response
        The responses from switching to Workspace Carlos and Workspace Amir.
    user_workspace_responses
        The responses from setting up multiple workspaces
    """

    original_suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    for response in suzin_switch_workspaces_response.values():
        json_response = response.json()
        assert json_response["access_token"] != original_suzin_access_token
        assert json_response["username"] == "Suzin"
        assert json_response["workspace_name"] in ["Workspace_Amir", "Workspace_Carlos"]


@when(
    "Mark tries to switch to Workspace Carlos and Workspace Amir",
    target_fixture="mark_switch_workspaces_response",
)
def mark_switches_workspaces(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> dict[str, httpx.Response]:
    """Mark switches to Workspace Carlos and Workspace Amir.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    dict[str, httpx.Response]
        The responses from switching to Workspace Carlos and Workspace Amir.
    """

    mark_access_token = user_workspace_responses["mark"]["access_token"]
    switch_to_workspace_carlos_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {mark_access_token}"},
        json={"workspace_name": "Workspace_Carlos"},
    )
    switch_to_workspace_amir_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {mark_access_token}"},
        json={"workspace_name": "Workspace_Amir"},
    )
    return {
        "switch_to_workspace_carlos_response": switch_to_workspace_carlos_response,
        "switch_to_workspace_amir_response": switch_to_workspace_amir_response,
    }


@then("Mark should get an error")
def check_mark_workspace_switch_responses(
    mark_switch_workspaces_response: dict[str, httpx.Response],
) -> None:
    """Check that Mark is not allowed to switch workspaces.

    Parameters
    ----------
    mark_switch_workspaces_response
        The responses from switching to Workspace Carlos and Workspace Amir.
    """

    for response in mark_switch_workspaces_response.values():
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@when(
    "Carlos tries to switch to Workspace Suzin and Workspace Amir",
    target_fixture="carlos_switch_workspaces_response",
)
def carlos_switches_workspaces(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> dict[str, httpx.Response]:
    """Carlos switches to Workspace Suzin and Workspace Amir.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    dict[str, httpx.Response]
        The responses from switching to Workspace Suzin and Workspace Amir.
    """

    carlos_access_token = user_workspace_responses["carlos"]["access_token"]
    switch_to_workspace_suzin_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {carlos_access_token}"},
        json={"workspace_name": "Workspace_Suzin"},
    )
    switch_to_workspace_amir_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {carlos_access_token}"},
        json={"workspace_name": "Workspace_Amir"},
    )
    return {
        "switch_to_workspace_suzin_response": switch_to_workspace_suzin_response,
        "switch_to_workspace_amir_response": switch_to_workspace_amir_response,
    }


@then("Carlos should get an error")
def check_carlos_workspace_switch_responses(
    carlos_switch_workspaces_response: dict[str, httpx.Response],
) -> None:
    """Check that Carlos is not allowed to switch workspaces.

    Parameters
    ----------
    carlos_switch_workspaces_response
        The responses from switching to Workspace Suzin and Workspace Amir.
    """

    for response in carlos_switch_workspaces_response.values():
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@when(
    "Zia tries to switch to Workspace Suzin and Workspace Amir",
    target_fixture="zia_switch_workspaces_response",
)
def zia_switches_workspaces(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> dict[str, httpx.Response]:
    """Zia switches to Workspace Suzin and Workspace Amir.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    dict[str, httpx.Response]
        The responses from switching to Workspace Suzin and Workspace Amir.
    """

    zia_access_token = user_workspace_responses["zia"]["access_token"]
    switch_to_workspace_suzin_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {zia_access_token}"},
        json={"workspace_name": "Workspace_Suzin"},
    )
    switch_to_workspace_amir_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {zia_access_token}"},
        json={"workspace_name": "Workspace_Amir"},
    )
    return {
        "switch_to_workspace_suzin_response": switch_to_workspace_suzin_response,
        "switch_to_workspace_amir_response": switch_to_workspace_amir_response,
    }


@then("Zia should get an error")
def check_zia_workspace_switch_responses(
    zia_switch_workspaces_response: dict[str, httpx.Response],
) -> None:
    """Check that Zia is not allowed to switch workspaces.

    Parameters
    ----------
    zia_switch_workspaces_response
        The responses from switching to Workspace Suzin and Workspace Amir.
    """

    for response in zia_switch_workspaces_response.values():
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@when(
    "Amir tries to switch to Workspace Suzin and Workspace Carlos",
    target_fixture="amir_switch_workspaces_response",
)
def amir_switches_workspaces(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> dict[str, httpx.Response]:
    """Amir switches to Workspace Suzin and Workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces

    Returns
    -------
    dict[str, httpx.Response]
        The responses from switching to Workspace Suzin and Workspace Carlos.
    """

    amir_access_token = user_workspace_responses["amir"]["access_token"]
    switch_to_workspace_suzin_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {amir_access_token}"},
        json={"workspace_name": "Workspace_Suzin"},
    )
    switch_to_workspace_carlos_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {amir_access_token}"},
        json={"workspace_name": "Workspace_Carlos"},
    )
    return {
        "switch_to_workspace_suzin_response": switch_to_workspace_suzin_response,
        "switch_to_workspace_carlos_response": switch_to_workspace_carlos_response,
    }


@then("Amir should get an error")
def check_amir_workspace_switch_responses(
    amir_switch_workspaces_response: dict[str, httpx.Response],
) -> None:
    """Check that Amir is not allowed to switch workspaces.

    Parameters
    ----------
    amir_switch_workspaces_response
        The responses from switching to Workspace Suzin and Workspace Carlos.
    """

    for response in amir_switch_workspaces_response.values():
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@when(
    "Sid tries to switch to Workspace Suzin and Workspace Carlos",
    target_fixture="sid_switch_workspaces_response",
)
def sid_switches_workspaces(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> dict[str, httpx.Response]:
    """Sid switches to Workspace Suzin and Workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces

    Returns
    -------
    dict[str, httpx.Response]
        The responses from switching to Workspace Suzin and Workspace Carlos.
    """

    sid_access_token = user_workspace_responses["sid"]["access_token"]
    switch_to_workspace_suzin_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {sid_access_token}"},
        json={"workspace_name": "Workspace_Suzin"},
    )
    switch_to_workspace_carlos_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {sid_access_token}"},
        json={"workspace_name": "Workspace_Carlos"},
    )
    return {
        "switch_to_workspace_suzin_response": switch_to_workspace_suzin_response,
        "switch_to_workspace_carlos_response": switch_to_workspace_carlos_response,
    }


@then("Sid should get an error")
def check_sid_workspace_switch_responses(
    sid_switch_workspaces_response: dict[str, httpx.Response],
) -> None:
    """Check that Sid is not allowed to switch workspaces.

    Parameters
    ----------
    sid_switch_workspaces_response
        The responses from switching to Workspace Suzin and Workspace Carlos.
    """

    for response in sid_switch_workspaces_response.values():
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@when(
    "Poornima switches to Workspace Suzin",
    target_fixture="poornima_switch_workspace_response",
)
def poornima_switches_workspace(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> dict[str, httpx.Response]:
    """Poornima switches to Workspace Suzin.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    dict[str, httpx.Response]
        The response from switching to Workspace Suzin.
    """

    poornima_access_token = user_workspace_responses["poornima"]["access_token"]
    switch_to_workspace_suzin_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {poornima_access_token}"},
        json={"workspace_name": "Workspace_Suzin"},
    )
    return {"switch_to_workspace_suzin_response": switch_to_workspace_suzin_response}


@then("Poornima should be able to switch to Workspace Suzin")
def check_poornima_workspace_switch_response(
    poornima_switch_workspace_response: dict[str, httpx.Response],
    user_workspace_responses: dict[str, dict[str, Any]],
) -> None:
    """Check that Poornima can switch to workspace Suzin.

    Parameters
    ----------
    poornima_switch_workspace_response
        The responses from switching to Workspace Suzin.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    original_poornima_access_token = user_workspace_responses["poornima"][
        "access_token"
    ]
    for response in poornima_switch_workspace_response.values():
        json_response = response.json()
        assert json_response["access_token"] != original_poornima_access_token
        assert json_response["username"] == "Poornima"
        assert json_response["workspace_name"] in ["Workspace_Amir", "Workspace_Suzin"]
