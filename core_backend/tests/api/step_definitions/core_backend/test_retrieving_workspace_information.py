"""This module contains scenarios for testing retrieving workspace information."""

from typing import Any

import httpx
from fastapi import status
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from core_backend.app.config import DEFAULT_API_QUOTA, DEFAULT_CONTENT_QUOTA

# Define scenario(s).
scenarios("core_backend/retrieving_workspace_information.feature")


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


# Scenario: Admin retrieving information using workspace ID
@when(
    "Suzin retrieves information for workspace Suzin",
    target_fixture="suzin_retrieved_workspace_by_workspace_id_response",
)
def suzin_retrieve_workspace_information_by_workspace_id(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Suzin retrieves information for workspace Suzin.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Suzin retrieving workspace information by workspace ID.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    suzin_workspace_id = user_workspace_responses["suzin"]["workspace_name_to_id"][
        "Workspace_Suzin"
    ]
    retrieve_workspaces_response = client.get(
        f"/workspace/{suzin_workspace_id}",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
    )
    assert retrieve_workspaces_response.status_code == status.HTTP_200_OK
    return retrieve_workspaces_response


@then("Suzin should be able to see information regarding workspace Suzin only")
def check_suzin_workspace_info_by_workspace_id(
    suzin_retrieved_workspace_by_workspace_id_response: httpx.Response,
    user_workspace_responses: dict[str, dict[str, Any]],
) -> None:
    """Check that Suzin should be able to see information regarding workspace Suzin
    only.

    Parameters
    ----------
    suzin_retrieved_workspace_by_workspace_id_response
        The response from Suzin retrieving workspace information by workspace ID.
    user_workspace_responses
        The responses from setting up multiple workspaces.
    """

    suzin_workspace_id = user_workspace_responses["suzin"]["workspace_name_to_id"][
        "Workspace_Suzin"
    ]
    json_response = suzin_retrieved_workspace_by_workspace_id_response.json()
    assert json_response["api_daily_quota"] is None
    assert json_response["content_quota"] is None
    assert json_response["workspace_id"] == suzin_workspace_id
    assert json_response["workspace_name"] == "Workspace_Suzin"


@when(
    "Carlos retrieves information for workspace Suzin",
    target_fixture="carlos_retrieved_workspace_by_workspace_id_response",
)
def carlos_retrieve_workspace_information_by_workspace_id(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Carlos retrieves information for workspace Suzin.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Carlos retrieving workspace information by workspace ID.
    """

    carlos_access_token = user_workspace_responses["carlos"]["access_token"]
    suzin_workspace_id = user_workspace_responses["suzin"]["workspace_name_to_id"][
        "Workspace_Suzin"
    ]
    retrieve_workspaces_response = client.get(
        f"/workspace/{suzin_workspace_id}",
        headers={"Authorization": f"Bearer {carlos_access_token}"},
    )
    return retrieve_workspaces_response


@then("Carlos should get an error")
def check_carlos_workspace_info_by_workspace_id(
    carlos_retrieved_workspace_by_workspace_id_response: httpx.Response,
) -> None:
    """Check that Carlos should get an error.

    Parameters
    ----------
    carlos_retrieved_workspace_by_workspace_id_response
        The response from Carlos retrieving workspace information by workspace ID.
    """

    assert (
        carlos_retrieved_workspace_by_workspace_id_response.status_code
        == status.HTTP_403_FORBIDDEN
    )


# Scenario: Non-admins retrieving information using workspace ID
@when(
    "Sid retrieves information for workspace Amir",
    target_fixture="sid_retrieved_workspace_by_workspace_id_response",
)
def sid_retrieve_workspace_information_by_workspace_id(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Sid retrieves information for workspace Amir.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Sid retrieving workspace information by workspace ID.
    """

    sid_access_token = user_workspace_responses["sid"]["access_token"]
    amir_workspace_id = user_workspace_responses["amir"]["workspace_name_to_id"][
        "Workspace_Amir"
    ]
    retrieve_workspaces_response = client.get(
        f"/workspace/{amir_workspace_id}",
        headers={"Authorization": f"Bearer {sid_access_token}"},
    )
    return retrieve_workspaces_response


@then("Sid should get an error")
def check_sid_workspace_info_by_workspace_id(
    sid_retrieved_workspace_by_workspace_id_response: httpx.Response,
) -> None:
    """Check that Sid should get an error.

    Parameters
    ----------
    sid_retrieved_workspace_by_workspace_id_response
        The response from Sid retrieving workspace information by workspace ID.
    """

    assert (
        sid_retrieved_workspace_by_workspace_id_response.status_code
        == status.HTTP_403_FORBIDDEN
    )


# Scenario: Admins retrieving workspaces using user ID
@when(
    "Suzin retrieves workspace information for Poornima",
    target_fixture="suzin_retrieved_workspace_by_user_id_response",
)
def suzin_retrieve_workspace_information_by_user_id(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Suzin retrieves workspace information for Poornima.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Suzin retrieving workspace information by user ID.
    """

    suzin_access_token = user_workspace_responses["suzin"]["access_token"]
    poornima_user_id = user_workspace_responses["poornima"]["user_id"]
    retrieve_workspaces_response = client.get(
        f"/workspace/get-user-workspaces/{poornima_user_id}",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
    )
    assert retrieve_workspaces_response.status_code == status.HTTP_200_OK
    return retrieve_workspaces_response


@then(
    "Suzin should be able to see information for all workspaces that Poornima belongs "
    "to"
)
def check_suzin_workspace_info_by_user_id(
    suzin_retrieved_workspace_by_user_id_response: httpx.Response,
) -> None:
    """Check that Suzin should be able to see information for all workspaces that
    Poornima

    Parameters
    ----------
    suzin_retrieved_workspace_by_user_id_response
        The response from Suzin retrieving workspace information by user ID.
    """

    json_responses = suzin_retrieved_workspace_by_user_id_response.json()
    assert len(json_responses) == 2
    for dict_ in json_responses:
        assert dict_["workspace_name"] in ["Workspace_Suzin", "Workspace_Amir"]


@when(
    "Amir retrieves workspace information for Poornima",
    target_fixture="amir_retrieved_workspace_by_user_id_response",
)
def amir_retrieve_workspace_information_by_user_id(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Amir retrieves workspace information for Poornima.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Amir retrieving workspace information by user ID.
    """

    amir_access_token = user_workspace_responses["amir"]["access_token"]
    poornima_user_id = user_workspace_responses["poornima"]["user_id"]
    retrieve_workspaces_response = client.get(
        f"/workspace/get-user-workspaces/{poornima_user_id}",
        headers={"Authorization": f"Bearer {amir_access_token}"},
    )
    assert retrieve_workspaces_response.status_code == status.HTTP_200_OK
    return retrieve_workspaces_response


@then("Amir should only see information for Poornima in workspace Amir")
def check_amir_workspace_info_by_user_id(
    amir_retrieved_workspace_by_user_id_response: httpx.Response,
) -> None:
    """Check that Amir should only see information for Poornima in workspace Amir.

    Parameters
    ----------
    amir_retrieved_workspace_by_user_id_response
        The response from Amir retrieving workspace information by user ID.
    """

    json_responses = amir_retrieved_workspace_by_user_id_response.json()
    assert len(json_responses) == 1
    json_response = json_responses[0]
    assert json_response["api_daily_quota"] == DEFAULT_API_QUOTA
    assert json_response["content_quota"] == DEFAULT_CONTENT_QUOTA
    assert json_response["workspace_name"] == "Workspace_Amir"


@when(
    "Carlos retrieves workspace information for Poornima",
    target_fixture="carlos_retrieved_workspace_by_user_id_response",
)
def carlos_retrieve_workspace_information_by_user_id(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Carlos retrieves workspace information for Poornima.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Carlos retrieving workspace information by user ID.
    """

    carlos_access_token = user_workspace_responses["carlos"]["access_token"]
    poornima_user_id = user_workspace_responses["poornima"]["user_id"]
    retrieve_workspaces_response = client.get(
        f"/workspace/get-user-workspaces/{poornima_user_id}",
        headers={"Authorization": f"Bearer {carlos_access_token}"},
    )
    return retrieve_workspaces_response


@then("Carlos should get an error again")
def check_carlos_workspace_info_by_user_id(
    carlos_retrieved_workspace_by_user_id_response: httpx.Response,
) -> None:
    """Check that Carlos should get an error.

    Parameters
    ----------
    carlos_retrieved_workspace_by_user_id_response
        The response from Carlos retrieving workspace information by user ID.
    """

    assert (
        carlos_retrieved_workspace_by_user_id_response.status_code
        == status.HTTP_403_FORBIDDEN
    )


# Scenario: Non-admins retrieving workspaces using user ID
@when(
    "Mark retrieves information for workspace Suzin",
    target_fixture="mark_retrieved_workspace_by_user_id_response",
)
def mark_retrieve_workspace_information_by_user_id(
    client: TestClient, user_workspace_responses: dict[str, dict[str, Any]]
) -> httpx.Response:
    """Mark retrieves workspace information for Suzin.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    user_workspace_responses
        The responses from setting up multiple workspaces.

    Returns
    -------
    httpx.Response
        The response from Mark retrieving workspace information by user ID.
    """

    mark_access_token = user_workspace_responses["mark"]["access_token"]
    suzin_user_id = user_workspace_responses["suzin"]["user_id"]
    retrieve_workspaces_response = client.get(
        f"/workspace/get-user-workspaces/{suzin_user_id}",
        headers={"Authorization": f"Bearer {mark_access_token}"},
    )
    return retrieve_workspaces_response


@then("Mark should get an error")
def check_mark_workspace_info_by_user_id(
    mark_retrieved_workspace_by_user_id_response: httpx.Response,
) -> None:
    """Check that Mark should get an error.

    Parameters
    ----------
    mark_retrieved_workspace_by_user_id_response
        The response from Mark retrieving workspace information by user ID.
    """

    assert (
        mark_retrieved_workspace_by_user_id_response.status_code
        == status.HTTP_403_FORBIDDEN
    )
