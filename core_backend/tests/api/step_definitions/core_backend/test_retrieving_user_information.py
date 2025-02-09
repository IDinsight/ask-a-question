"""This module contains scenarios for testing retrieving user information."""

from typing import Any

import httpx
from fastapi import status
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

# Define scenario(s).
scenarios("core_backend/retrieving_user_information.feature")


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


# Scenario: Retrieved user information should be limited by role and workspace
@when(
    "Suzin retrieves information from all workspaces",
    target_fixture="suzin_retrieved_users_response",
)
def suzin_retrieve_users_information(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> list[httpx.Response]:
    """Suzin retrieves user information from all workspaces.

    NB: Suzin is a power user with access to multiple workspaces. Thus, Suzin should be
    able to retrieve user information from all the workspaces she has access to.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    list[httpx.Response]
        The responses from Suzin retrieving users information.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    retrieve_workspaces_response = client.get(
        "/workspace/", headers={"Authorization": f"Bearer {suzin_access_token}"}
    )
    json_response = retrieve_workspaces_response.json()
    assert len(json_response) == 3
    all_retrieved_users_responses = []
    for dict_ in json_response:
        switch_to_workspace_response = client.post(
            "/workspace/switch-workspace",
            headers={"Authorization": f"Bearer {suzin_access_token}"},
            json={"workspace_name": dict_["workspace_name"]},
        )
        access_token = switch_to_workspace_response.json()["access_token"]
        retrieved_users_response = client.get(
            "/user", headers={"Authorization": f"Bearer {access_token}"}
        )
        all_retrieved_users_responses.append(retrieved_users_response)
    return all_retrieved_users_responses


@then("Suzin should be able to see all users from all workspaces")
def check_suzin_has_access_to_all_users(
    suzin_retrieved_users_response: list[httpx.Response],
) -> None:
    """Check that Suzin can see user information from all workspaces.

    Parameters
    ----------
    suzin_retrieved_users_response
        The responses from Suzin retrieving users information.
    """

    assert len(suzin_retrieved_users_response) == 3
    for response in suzin_retrieved_users_response:
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        workspace_name = json_response[0]["user_workspaces"][0]["workspace_name"]
        for dict_ in json_response:
            assert dict_["user_workspaces"][0]["workspace_name"] == workspace_name
            match workspace_name:
                case "Workspace_Suzin":
                    assert dict_["username"] in ["Suzin", "Mark", "Poornima"]
                    assert len(json_response) == 3
                case "Workspace_Carlos":
                    assert dict_["username"] in ["Suzin", "Carlos", "Zia"]
                    assert len(json_response) == 3
                case _:
                    assert dict_["username"] in ["Suzin", "Amir", "Poornima", "Sid"]
                    assert len(json_response) == 4


@when(
    "Mark retrieves information from all workspaces",
    target_fixture="mark_retrieved_users_response",
)
def mark_retrieve_users_information(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Mark retrieves user information from all workspaces.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Mark retrieving users information.
    """

    mark_access_token = user_workspace_responses["mark"]["access_token"]
    retrieve_workspaces_response = client.get(
        "/workspace/", headers={"Authorization": f"Bearer {mark_access_token}"}
    )
    assert retrieve_workspaces_response.status_code == status.HTTP_403_FORBIDDEN
    retrieve_workspaces_response = client.get(
        "/workspace/current-workspace",
        headers={"Authorization": f"Bearer {mark_access_token}"},
    )
    return retrieve_workspaces_response


@then("Mark should only see his own information")
def check_mark_can_only_access_his_own_information(
    mark_retrieved_users_response: httpx.Response,
) -> None:
    """Check that Mark can only see his own information.

    Parameters
    ----------
    mark_retrieved_users_response
        The responses from Mark retrieving users information.
    """

    assert mark_retrieved_users_response.status_code == status.HTTP_200_OK
    json_response = mark_retrieved_users_response.json()
    assert json_response["api_daily_quota"] is None
    assert json_response["content_quota"] is None
    assert json_response["workspace_name"] == "Workspace_Suzin"


@when(
    "Carlos retrieves information from all workspaces",
    target_fixture="carlos_retrieved_users_response",
)
def carlos_retrieve_users_information(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> list[httpx.Response]:
    """Carlos retrieves user information from all workspaces.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    list[httpx.Response]
        The response from Carlos retrieving users information.
    """

    carlos_access_token = user_workspace_responses["carlos"]["access_token"]
    retrieve_workspaces_response = client.get(
        "/workspace/", headers={"Authorization": f"Bearer {carlos_access_token}"}
    )
    json_response = retrieve_workspaces_response.json()
    assert len(json_response) == 1
    all_retrieved_users_responses = []
    for dict_ in json_response:
        switch_to_workspace_response = client.post(
            "/workspace/switch-workspace",
            headers={"Authorization": f"Bearer {carlos_access_token}"},
            json={"workspace_name": dict_["workspace_name"]},
        )
        access_token = switch_to_workspace_response.json()["access_token"]
        retrieved_users_response = client.get(
            "/user", headers={"Authorization": f"Bearer {access_token}"}
        )
        all_retrieved_users_responses.append(retrieved_users_response)
    return all_retrieved_users_responses


@then("Carlos should only see users in his workspaces")
def check_carlos_has_access_to_his_users_only(
    carlos_retrieved_users_response: list[httpx.Response],
) -> None:
    """Check that Carlos can only see user information from his workspaces.

    Parameters
    ----------
    carlos_retrieved_users_response
        The responses from Carlos retrieving users information.
    """

    assert len(carlos_retrieved_users_response) == 1
    assert carlos_retrieved_users_response[0].status_code == status.HTTP_200_OK
    json_response = carlos_retrieved_users_response[0].json()
    assert len(json_response) == 3
    workspace_name = "Workspace_Carlos"
    for dict_ in json_response:
        assert dict_["user_workspaces"][0]["workspace_name"] == workspace_name
        assert dict_["username"] in ["Suzin", "Carlos", "Zia"]


@when(
    "Poornima retrieves information from her workspaces",
    target_fixture="poornima_retrieved_users_response",
)
def poornima_retrieve_users_information(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> list[httpx.Response]:
    """Poornima retrieves user information from her workspaces.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    list[httpx.Response]
        The response from Poornima retrieving users information.
    """

    poornima_access_token = user_workspace_responses["poornima"]["access_token"]
    retrieve_workspaces_response = client.get(
        "/workspace/", headers={"Authorization": f"Bearer {poornima_access_token}"}
    )
    json_response = retrieve_workspaces_response.json()
    assert len(json_response) == 2
    all_retrieved_users_responses = []
    for dict_ in json_response:
        switch_to_workspace_response = client.post(
            "/workspace/switch-workspace",
            headers={"Authorization": f"Bearer {poornima_access_token}"},
            json={"workspace_name": dict_["workspace_name"]},
        )
        access_token = switch_to_workspace_response.json()["access_token"]
        retrieved_users_response = client.get(
            "/user", headers={"Authorization": f"Bearer {access_token}"}
        )
        all_retrieved_users_responses.append(retrieved_users_response)
    return all_retrieved_users_responses


@then("Poornima should be able to see all users in her workspaces")
def check_poornima_has_access_to_her_users_only(
    poornima_retrieved_users_response: list[httpx.Response],
) -> None:
    """Check that Poornima can only see user information from her workspaces.

    Parameters
    ----------
    poornima_retrieved_users_response
        The responses from Poornima retrieving users information.
    """

    assert len(poornima_retrieved_users_response) == 2
    for response in poornima_retrieved_users_response:
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        workspace_name = json_response[0]["user_workspaces"][0]["workspace_name"]
        for dict_ in json_response:
            assert dict_["user_workspaces"][0]["workspace_name"] == workspace_name
            match workspace_name:
                case "Workspace_Suzin":
                    assert dict_["username"] in ["Suzin", "Mark", "Poornima"]
                    assert len(json_response) == 3
                case _:
                    assert dict_["username"] in ["Suzin", "Amir", "Poornima", "Sid"]
                    assert len(json_response) == 4
