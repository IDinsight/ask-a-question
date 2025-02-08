"""This module contains scenarios for testing removing users from workspaces."""

from typing import Any

import httpx
from fastapi import status
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

# Define scenario(s).
scenarios("core_backend/removing_users_from_workspaces.feature")


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
    "Carlos removes Suzin from workspace Carlos",
    target_fixture="suzin_remove_response",
)
def remove_suzin_from_workspace_carlos(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> None:
    """Carlos removes Suzin from workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    carlos_access_token = user_workspace_responses["carlos"]["access_token"]
    suzin_user_id = user_workspace_responses["suzin"]["user_id"]
    remove_response = client.delete(
        f"/user/{suzin_user_id}?remove_from_workspace_name=Workspace_Carlos",
        headers={"Authorization": f"Bearer {carlos_access_token}"},
    )
    assert remove_response.status_code == status.HTTP_200_OK
    json_response = remove_response.json()
    assert json_response["default_workspace_name"] == "Workspace_Suzin"
    assert json_response["removed_from_workspace_name"] == "Workspace_Carlos"
    assert json_response["require_authentication"] is False
    assert json_response["require_workspace_switch"] is False


@then("Suzin should only belong to workspace Suzin and workspace Amir")
def check_suzin_does_not_belong_to_workspace_carlos(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> None:
    """Check that Suzin only belongs to workspace Suzin and workspace Amir.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    suzin_user_id = user_workspace_responses["suzin"]["user_id"]
    suzin_workspaces_response = client.get(
        f"/workspace/get-user-workspaces/{suzin_user_id}",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
    )
    assert suzin_workspaces_response.status_code == status.HTTP_200_OK
    assert len(suzin_workspaces_response.json()) == 2
    json_response = suzin_workspaces_response.json()
    for dict_ in json_response:
        assert dict_["workspace_name"] in ["Workspace_Suzin", "Workspace_Amir"]


@when(
    "Carlos then tries to remove himself from workspace Carlos",
    target_fixture="carlos_remove_response",
)
def remove_carlos_from_workspace_carlos(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Carlos tries to remove himself from workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Carlos trying to remove himself from workspace Carlos.
    """

    carlos_access_token = user_workspace_responses["carlos"]["access_token"]
    carlos_user_id = user_workspace_responses["carlos"]["user_id"]
    remove_response = client.delete(
        f"/user/{carlos_user_id}?remove_from_workspace_name=Workspace_Carlos",
        headers={"Authorization": f"Bearer {carlos_access_token}"},
    )
    return remove_response


@then("Carlos should get an error")
def check_carlos_cannot_remove_himself_from_workspace_carlos(
    client: TestClient,
    carlos_remove_response: httpx.Response,
    user_workspace_responses: dict[str, dict[str, Any]],
) -> None:
    """Check that Carlos cannot remove himself from workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    carlos_remove_response
        The response from Carlos trying to remove himself from workspace Carlos.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    assert carlos_remove_response.status_code == status.HTTP_403_FORBIDDEN

    carlos_access_token = user_workspace_responses["carlos"]["access_token"]
    carlos_user_id = user_workspace_responses["carlos"]["user_id"]
    carlos_workspaces_response = client.get(
        f"/workspace/get-user-workspaces/{carlos_user_id}",
        headers={"Authorization": f"Bearer {carlos_access_token}"},
    )
    assert carlos_workspaces_response.status_code == status.HTTP_200_OK
    assert len(carlos_workspaces_response.json()) == 1
    json_response = carlos_workspaces_response.json()
    assert json_response[0]["workspace_name"] == "Workspace_Carlos"


@when(
    "Amir removes Sid from workspace Amir",
    target_fixture="sid_remove_response",
)
def remove_sid_from_workspace_amir(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> None:
    """Amir removes Sid from workspace Amir.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    amir_access_token = user_workspace_responses["amir"]["access_token"]
    sid_user_id = user_workspace_responses["sid"]["user_id"]
    remove_response = client.delete(
        f"/user/{sid_user_id}?remove_from_workspace_name=Workspace_Amir",
        headers={"Authorization": f"Bearer {amir_access_token}"},
    )
    assert remove_response.status_code == status.HTTP_200_OK
    json_response = remove_response.json()
    assert json_response["default_workspace_name"] is None
    assert json_response["removed_from_workspace_name"] == "Workspace_Amir"
    assert json_response["require_authentication"] is False
    assert json_response["require_workspace_switch"] is False


@then("Sid no longer belongs to workspace Amir")
def check_sid_does_not_belong_to_workspace_amir(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> None:
    """Check that Sid no longer belongs to workspace Amir.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    amir_access_token = user_workspace_responses["amir"]["access_token"]
    users_response = client.get(
        "/user/", headers={"Authorization": f"Bearer {amir_access_token}"}
    )
    json_response = users_response.json()
    assert len(json_response) == 3
    for dict_ in json_response:
        assert dict_["username"] in ["Suzin", "Poornima", "Amir"]


@then("Sid can no longer authenticate")
def check_sid_cannot_authenticate(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> None:
    """Check that Sid can no longer authenticate.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    sid_access_token = user_workspace_responses["sid"]["access_token"]
    user_response = client.get(
        "/user/current-user", headers={"Authorization": f"Bearer {sid_access_token}"}
    )
    assert user_response.status_code == status.HTTP_401_UNAUTHORIZED


@when(
    "Amir tries to remove Poornima from workspace Suzin",
    target_fixture="poornima_remove_response",
)
def remove_poornima_from_workspace_suzin(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Amir tries to remove Poornima from workspace Suzin.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Amir trying to remove Poornima from workspace Suzin.
    """

    amir_access_token = user_workspace_responses["amir"]["access_token"]
    poornima_user_id = user_workspace_responses["poornima"]["user_id"]
    remove_response = client.delete(
        f"/user/{poornima_user_id}?remove_from_workspace_name=Workspace_Suzin",
        headers={"Authorization": f"Bearer {amir_access_token}"},
    )
    return remove_response


@then("Amir should get an error")
def check_amir_cannot_remove_poornima_from_workspace_suzin(
    poornima_remove_response: httpx.Response,
) -> None:
    """Check that Sid can no longer authenticate.

    Parameters
    ----------
    poornima_remove_response
        The response from Amir trying to remove Poornima from workspace Suzin.
    """

    assert poornima_remove_response.status_code == status.HTTP_403_FORBIDDEN


@when(
    "Poornima removes herself from workspace Amir",
    target_fixture="poornima_self_remove_response",
)
def remove_poornima_from_workspace_amir(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Poorima removes herself from workspace Amir.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Poornima removing herself from workspace Amir.
    """

    poornima_access_token = user_workspace_responses["poornima"]["access_token"]
    poornima_user_id = user_workspace_responses["poornima"]["user_id"]
    remove_response = client.delete(
        f"/user/{poornima_user_id}?remove_from_workspace_name=Workspace_Amir",
        headers={"Authorization": f"Bearer {poornima_access_token}"},
    )
    assert remove_response.status_code == status.HTTP_200_OK
    return remove_response


@then("Poornima is required to switch workspaces to workspace Suzin")
def check_that_poornima_is_required_to_switch_workspaces(
    poornima_self_remove_response: httpx.Response,
) -> None:
    """Check that Poornima is required to switch workspaces.

    Parameters
    ----------
    poornima_self_remove_response
        The response from Poornima removing herself from workspace Amir.
    """

    json_response = poornima_self_remove_response.json()
    assert json_response["default_workspace_name"] == "Workspace_Suzin"
    assert json_response["removed_from_workspace_name"] == "Workspace_Amir"
    assert json_response["require_authentication"] is False
    assert json_response["require_workspace_switch"] is True


@when(
    "Carlos removes himself from workspace Carlos",
    target_fixture="carlos_self_remove_response",
)
def remove_carlos_from_workspace_carlos_(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Carlos removes himself from workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Carlos removing himself from workspace Carlos.
    """

    carlos_access_token = user_workspace_responses["carlos"]["access_token"]
    carlos_user_id = user_workspace_responses["carlos"]["user_id"]
    remove_response = client.delete(
        f"/user/{carlos_user_id}?remove_from_workspace_name=Workspace_Carlos",
        headers={"Authorization": f"Bearer {carlos_access_token}"},
    )
    assert remove_response.status_code == status.HTTP_200_OK
    return remove_response


@then("Carlos no longer belongs to workspace Carlos")
def check_carlos_does_not_belong_to_workspace_carlos(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> None:
    """Check that Carlos no longer belongs to workspace Carlos.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    switch_to_workspace_carlos_response = client.post(
        "/workspace/switch-workspace",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={"workspace_name": "Workspace_Carlos"},
    )
    access_token = switch_to_workspace_carlos_response.json()["access_token"]
    users_response = client.get(
        "/user/", headers={"Authorization": f"Bearer {access_token}"}
    )
    json_response = users_response.json()
    assert len(json_response) == 2
    for dict_ in json_response:
        assert dict_["username"] in ["Suzin", "Zia"]


@then("Carlos can no longer authenticate")
def check_carlos_cannot_authenticate(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> None:
    """Check that Carlos can no longer authenticate.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    carlos_access_token = user_workspace_responses["carlos"]["access_token"]
    user_response = client.get(
        "/user/current-user", headers={"Authorization": f"Bearer {carlos_access_token}"}
    )
    assert user_response.status_code == status.HTTP_401_UNAUTHORIZED


@then("Reauthentication is required")
def check_authentication_is_required(
    carlos_self_remove_response: httpx.Response,
) -> None:
    """Check that reauthentication is required again after Carlos removes himself from
    workspace Carlos.

    Parameters
    ----------
    carlos_self_remove_response
        The response from Carlos removing himself from workspace Carlos.
    """

    assert carlos_self_remove_response.status_code == status.HTTP_200_OK
    json_response = carlos_self_remove_response.json()
    assert json_response["default_workspace_name"] is None
    assert json_response["removed_from_workspace_name"] == "Workspace_Carlos"
    assert json_response["require_authentication"] is True
    assert json_response["require_workspace_switch"] is False
