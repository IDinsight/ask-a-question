"""This module contains scenarios for testing creating/adding users to workspaces."""

from typing import Any

import httpx
from fastapi import status
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from core_backend.app.users.schemas import UserRoles

# Define scenario(s).
scenarios("core_backend/adding_users.feature")


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


# Scenario: Creating a new user in an existing workspace
@when(
    "Carlos adds Tanmay to workspace Carlos",
    target_fixture="tanmay_create_response",
)
def carlos_adds_tanmay(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Carlos adds Tanmay to workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from adding Tanmay to workspace Carlos.
    """

    carlos_access_token = user_workspace_responses["carlos"]["access_token"]
    create_response = client.post(
        "/user/",
        headers={"Authorization": f"Bearer {carlos_access_token}"},
        json={
            "is_default_workspace": True,
            "password": "123",
            "role": UserRoles.READ_ONLY,
            "username": "Tanmay",
        },
    )
    assert create_response.status_code == status.HTTP_200_OK
    return create_response


@then("Tanmay should be added to workspace Carlos")
def check_tanmay_create_response(
    client: TestClient,
    tanmay_create_response: httpx.Response,
    user_workspace_responses: dict[str, dict[str, Any]],
) -> None:
    """Check that Tanmay was added to workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    tanmay_create_response
        The response object from adding Tanmay to workspace Carlos.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    json_response = tanmay_create_response.json()
    assert json_response["is_default_workspace"] is True
    assert json_response["role"] == UserRoles.READ_ONLY
    assert json_response["username"] == "Tanmay"
    assert json_response["workspace_name"] == "Workspace_Carlos"
    assert json_response["recovery_codes"]

    carlos_access_token = user_workspace_responses["carlos"]["access_token"]
    response = client.get(
        "/user/", headers={"Authorization": f"Bearer {carlos_access_token}"}
    )
    json_response = response.json()
    for dict_ in json_response:
        if dict_["username"] == "Tanmay":
            assert dict_["is_default_workspace"] == [True]
            assert dict_["user_workspaces"][0]["user_role"] == UserRoles.READ_ONLY
            assert dict_["user_workspaces"][0]["workspace_name"] == "Workspace_Carlos"
            assert dict_["username"] == "Tanmay"


# Scenario: Creating a new user in a workspace that does not exist
@when(
    "Carlos adds Jahnavi to workspace Jahnavi",
    target_fixture="jahnavi_create_response",
)
def carlos_adds_jahnavi(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Carlos adds Jahnavi to workspace Jahnavi.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from adding Jahnavi to workspace Jahnavi.
    """

    carlos_access_token = user_workspace_responses["carlos"]["access_token"]
    create_response = client.post(
        "/user/",
        headers={"Authorization": f"Bearer {carlos_access_token}"},
        json={
            "is_default_workspace": True,
            "password": "123",
            "role": UserRoles.ADMIN,
            "username": "Jahnavi",
            "workspace_name": "Workspace_Jahnavi",
        },
    )
    return create_response


@then("Carlos should get an error")
def check_jahnavi_create_response(jahnavi_create_response: httpx.Response) -> None:
    """Check that Carlos got an error.

    Parameters
    ----------
    jahnavi_create_response
        The response object from adding Jahnavi to workspace Jahnavi.
    """

    assert jahnavi_create_response.status_code == status.HTTP_400_BAD_REQUEST


# Scenario: Adding an existing user to a workspace that does not exist
@when(
    "Suzin adds Mark to workspace Mark",
    target_fixture="mark_add_response_fail",
)
def suzin_adds_mark_to_workspace_mark(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Suzin adds Mark to workspace Mark.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from adding Mark to workspace Mark.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    create_response = client.post(
        "/user/existing-user",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={
            "is_default_workspace": True,
            "role": UserRoles.ADMIN,
            "username": "Mark",
            "workspace_name": "Workspace_Mark",
        },
    )
    return create_response


@then("Suzin should get an error")
def check_mark_add_response_fail(mark_add_response_fail: httpx.Response) -> None:
    """Check that Suzin got an error.

    Parameters
    ----------
    mark_add_response_fail
        The response object from adding Mark to workspace Mark.
    """

    assert mark_add_response_fail.status_code == status.HTTP_400_BAD_REQUEST


# Scenario: Adding an existing user to an existing workspace
@when(
    "Suzin adds Mark to workspace Amir",
    target_fixture="mark_add_response_pass",
)
def suzin_adds_mark_to_workspace_amir(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Suzin adds Mark to workspace Amir.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from adding Mark to workspace Amir.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    create_response = client.post(
        "/user/existing-user",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={
            "is_default_workspace": True,
            "role": UserRoles.ADMIN,
            "username": "Mark",
            "workspace_name": "Workspace_Amir",
        },
    )
    assert create_response.status_code == status.HTTP_200_OK
    return create_response


@then("Mark should be added to workspace Amir")
def check_mark_add_response_pass(
    client: TestClient,
    mark_add_response_pass: httpx.Response,
    user_workspace_responses: dict[str, dict[str, Any]],
) -> None:
    """Check that Tanmay was added to workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    mark_add_response_pass
        The response object from adding Mark to workspace Amir.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    json_response = mark_add_response_pass.json()
    assert json_response["is_default_workspace"] is True
    assert json_response["role"] == UserRoles.ADMIN
    assert json_response["username"] == "Mark"
    assert json_response["workspace_name"] == "Workspace_Amir"
    assert json_response["recovery_codes"]

    mark_access_token = user_workspace_responses["mark"]["access_token"]
    response = client.get(
        "/user/current-user", headers={"Authorization": f"Bearer {mark_access_token}"}
    )
    json_response = response.json()
    for x, y in zip(
        json_response["is_default_workspace"], json_response["user_workspaces"]
    ):
        if x is True:
            assert y["user_role"] == UserRoles.ADMIN
            assert y["workspace_name"] == "Workspace_Amir"
        else:
            assert y["user_role"] == UserRoles.READ_ONLY
            assert y["workspace_name"] == "Workspace_Suzin"
    assert json_response["username"] == "Mark"
