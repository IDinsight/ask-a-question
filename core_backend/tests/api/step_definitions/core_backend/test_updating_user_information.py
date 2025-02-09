"""This module contains scenarios for testing updating user information."""

from typing import Any

import httpx
from fastapi import status
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from core_backend.app.users.schemas import UserRoles

# Define scenario(s).
scenarios("core_backend/updating_user_information.feature")


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


# Scenario: Admin updates admin's information
@when(
    "Suzin updates Poornima's name to Poornima_Updated",
    target_fixture="poornima_update_name_response",
)
def suzin_update_poornima_name(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Suzin updates Poornima's name to Poornima_Updated.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from updating Poornima's name.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    poornima_user_id = user_workspace_responses["poornima"]["user_id"]
    update_response = client.put(
        f"/user/{poornima_user_id}",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={"username": "Poornima_Updated"},
    )
    assert update_response.status_code == status.HTTP_200_OK
    return update_response


@then("Poornima's name should be Poornima_Updated")
def check_poornima_updated_name(
    poornima_update_name_response: httpx.Response,
    user_workspace_responses: dict[str, dict[str, Any]],
) -> None:
    """Check that Poornima's name is updated.

    Parameters
    ----------
    poornima_update_name_response
        The response object from updating Poornima's name.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    poornima_user_id = user_workspace_responses["poornima"]["user_id"]
    json_response = poornima_update_name_response.json()
    assert json_response["is_default_workspace"] == [False, True]
    assert json_response["user_id"] == poornima_user_id
    assert json_response["user_workspaces"][0]["workspace_name"] == "Workspace_Suzin"
    assert json_response["user_workspaces"][1]["workspace_name"] == "Workspace_Amir"
    assert json_response["username"] == "Poornima_Updated"


@when(
    "Suzin updates Poornima's default workspace to workspace Suzin",
    target_fixture="poornima_update_default_workspace_response",
)
def suzin_update_poornima_default_workspace(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Suzin updates Poornima's default workspace to workspace Suzin.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from updating Poornima's default workspace.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    poornima_user_id = user_workspace_responses["poornima"]["user_id"]
    update_response = client.put(
        f"/user/{poornima_user_id}",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={
            "is_default_workspace": True,
            "username": "Poornima_Updated",
            "workspace_name": "Workspace_Suzin",
        },
    )
    assert update_response.status_code == status.HTTP_200_OK
    return update_response


@then("Poornima's default workspace should be changed to workspace Suzin")
def check_poornima_updated_default_workspace(
    poornima_update_default_workspace_response: httpx.Response,
    user_workspace_responses: dict[str, dict[str, Any]],
) -> None:
    """Check that Poornima's default workspace is updated.

    Parameters
    ----------
    poornima_update_default_workspace_response
        The response object from updating Poornima's default workspace.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    poornima_user_id = user_workspace_responses["poornima"]["user_id"]
    json_response = poornima_update_default_workspace_response.json()
    assert json_response["is_default_workspace"] == [True, False]
    assert json_response["user_id"] == poornima_user_id
    assert json_response["user_workspaces"][0]["user_role"] == UserRoles.ADMIN
    assert json_response["user_workspaces"][0]["workspace_name"] == "Workspace_Suzin"
    assert json_response["user_workspaces"][1]["user_role"] == UserRoles.ADMIN
    assert json_response["user_workspaces"][1]["workspace_name"] == "Workspace_Amir"
    assert json_response["username"] == "Poornima_Updated"


@when(
    "Suzin updates Poornima's role to read-only in workspace Suzin",
    target_fixture="poornima_update_workspace_role_response",
)
def suzin_update_poornima_role(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Suzin updates Poornima's role in workspace Suzin.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from updating Poornima's role.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    poornima_user_id = user_workspace_responses["poornima"]["user_id"]
    update_response = client.put(
        f"/user/{poornima_user_id}",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={
            "role": UserRoles.READ_ONLY,
            "username": "Poornima_Updated",
            "workspace_name": "Workspace_Suzin",
        },
    )
    assert update_response.status_code == status.HTTP_200_OK
    return update_response


@then("Poornima's role should be read-only in workspace Suzin")
def check_poornima_updated_role(
    poornima_update_workspace_role_response: httpx.Response,
    user_workspace_responses: dict[str, dict[str, Any]],
) -> None:
    """Check that Poornima's role is updated.

    Parameters
    ----------
    poornima_update_workspace_role_response
        The response object from updating Poornima's role.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    poornima_user_id = user_workspace_responses["poornima"]["user_id"]
    json_response = poornima_update_workspace_role_response.json()
    assert json_response["is_default_workspace"] == [True, False]
    assert json_response["user_id"] == poornima_user_id
    assert json_response["user_workspaces"][0]["user_role"] == UserRoles.READ_ONLY
    assert json_response["user_workspaces"][0]["workspace_name"] == "Workspace_Suzin"
    assert json_response["user_workspaces"][1]["user_role"] == UserRoles.ADMIN
    assert json_response["user_workspaces"][1]["workspace_name"] == "Workspace_Amir"
    assert json_response["username"] == "Poornima_Updated"


# Scenario: Admin updates user's default workspace to a workspace that admin is not a
# member of
@when(
    "Amir updates Poornima's default workspace to workspace Suzin",
    target_fixture="poornima_update_default_workspace_response",
)
def amir_update_poornima_workspace(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Amir updates Poornima's default workspace to workspace Suzin.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from updating Poornima's default workspace.
    """

    amir_access_token = user_workspace_responses["amir"]["access_token"]
    poornima_user_id = user_workspace_responses["poornima"]["user_id"]
    update_response = client.put(
        f"/user/{poornima_user_id}",
        headers={"Authorization": f"Bearer {amir_access_token}"},
        json={
            "is_default_workspace": True,
            "username": "Poornima",
            "workspace_name": "Workspace_Suzin",
        },
    )
    return update_response


@then("Amir should get an error")
def check_poornima_updated_workspace(
    poornima_update_default_workspace_response: httpx.Response,
) -> None:
    """Check that Poornima's default workspace is not updated.

    Parameters
    ----------
    poornima_update_default_workspace_response
        The response object from updating Poornima's default workspace.
    """

    assert (
        poornima_update_default_workspace_response.status_code
        == status.HTTP_403_FORBIDDEN
    )


# Scenario: Admin updates read-only user's information
@when(
    "Poornima updates Sid's role to admin in workspace Amir",
    target_fixture="sid_update_role_response",
)
def poornima_update_sid_role(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Poornima updates Sid's role to admin in workspace Amir.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from updating Sid's role.
    """

    poornima_access_token = user_workspace_responses["poornima"]["access_token"]
    sid_user_id = user_workspace_responses["sid"]["user_id"]
    update_response = client.put(
        f"/user/{sid_user_id}",
        headers={"Authorization": f"Bearer {poornima_access_token}"},
        json={
            "role": UserRoles.ADMIN,
            "username": "Sid",
            "workspace_name": "Workspace_Amir",
        },
    )
    assert update_response.status_code == status.HTTP_200_OK
    return update_response


@then("Sid's role should be admin in workspace Amir")
def check_sid_updated_role(sid_update_role_response: httpx.Response) -> None:
    """Check that Sid's role is updated.

    Parameters
    ----------
    sid_update_role_response
        The response object from updating Sid's role.
    """

    json_response = sid_update_role_response.json()
    assert json_response["is_default_workspace"] == [True]
    assert json_response["user_workspaces"][0]["user_role"] == UserRoles.ADMIN
    assert json_response["user_workspaces"][0]["workspace_name"] == "Workspace_Amir"
    assert json_response["username"] == "Sid"


# Scenario: Admin updates information for a user not in admin's workspaces
@when(
    "Carlos updates Mark's information",
    target_fixture="mark_update_info_response",
)
def carlos_update_mark_info(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Carlos updates Mark's information.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from updating Mark's information.
    """

    carlos_access_token = user_workspace_responses["carlos"]["access_token"]
    mark_user_id = user_workspace_responses["mark"]["user_id"]
    update_response = client.put(
        f"/user/{mark_user_id}",
        headers={"Authorization": f"Bearer {carlos_access_token}"},
        json={
            "is_default_workspace": True,
            "role": UserRoles.ADMIN,
            "username": "Mark_Updated",
            "workspace_name": "Workspace_Suzin",
        },
    )
    return update_response


@then("Carlos should get an error")
def check_mark_updated_info(mark_update_info_response: httpx.Response) -> None:
    """Check that Mark's name is not updated.

    Parameters
    ----------
    mark_update_info_response
        The response object from updating Mark's information.
    """

    assert mark_update_info_response.status_code == status.HTTP_403_FORBIDDEN


# Scenario: Admin changes their user's workspace information to a workspace that the
# user is not a member of
@when(
    "Suzin updates Mark's workspace information to workspace Carlos",
    target_fixture="mark_update_workspace_info_response",
)
def carlos_update_mark_name(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Suzin updates Mark's workspace information to workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from updating Mark's workspace information.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    mark_user_id = user_workspace_responses["mark"]["user_id"]
    update_response = client.put(
        f"/user/{mark_user_id}",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={
            "is_default_workspace": True,
            "role": UserRoles.ADMIN,
            "username": "Mark",
            "workspace_name": "Workspace_Carlos",
        },
    )
    return update_response


@then("Suzin should get an error")
def check_mark_updated_workspace_info(
    mark_update_workspace_info_response: httpx.Response,
) -> None:
    """Check that Mark's workspace information is not updated.

    Parameters
    ----------
    mark_update_workspace_info_response
        The response object from updating Mark's workspace information.
    """

    assert (
        mark_update_workspace_info_response.status_code == status.HTTP_400_BAD_REQUEST
    )


# Scenario: Read-only user tries to update their own information
@when(
    "Zia tries to update his own role to admin in workspace Carlos",
    target_fixture="zia_update_role_response",
)
def zia_update_role(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Zia tries to update his own role to admin in workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response object from updating Zia's role.
    """

    zia_access_token = user_workspace_responses["zia"]["access_token"]
    zia_user_id = user_workspace_responses["zia"]["user_id"]
    update_response = client.put(
        f"/user/{zia_user_id}",
        headers={"Authorization": f"Bearer {zia_access_token}"},
        json={
            "role": UserRoles.ADMIN,
            "username": "Zia",
            "workspace_name": "Workspace_Carlos",
        },
    )
    return update_response


@then("Zia should get an error")
def check_zia_updated_role(zia_update_role_response: httpx.Response) -> None:
    """Check that Zia's role is not updated.

    Parameters
    ----------
    zia_update_role_response
        The response object from updating Zia's role.
    """

    assert zia_update_role_response.status_code == status.HTTP_403_FORBIDDEN
