"""This module contains fixtures for the API tests."""

from collections import defaultdict
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient
from pytest_bdd.parser import Feature, Scenario, Step
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.users.models import (
    UserDB,
    UserWorkspaceDB,
    WorkspaceDB,
    check_if_users_exist,
    get_user_by_username,
)
from core_backend.app.users.schemas import UserRoles
from core_backend.app.workspaces.utils import (
    check_if_workspaces_exist,
    get_workspace_by_workspace_name,
)


# Hooks.
def pytest_bdd_step_error(
    request: pytest.FixtureRequest,  # pylint: disable=W0613
    feature: Feature,  # pylint: disable=W0613
    scenario: Scenario,  # pylint: disable=W0613
    step: Step,
    step_func: Callable,
    step_func_args: dict[str, Any],
    exception: Exception,
) -> None:
    """Hook for when a step fails.

    Parameters
    ----------
    request
        Pytest fixture request object.
    feature
        The BDD feature that failed.
    scenario
        The BDD scenario that failed.
    step
        The BDD step that failed.
    step_func
        The step function that failed.
    step_func_args
        The arguments passed to the step function that failed.
    exception
        The exception that was raised by the step function that failed.
    """

    print(
        f"\n>>>STEP FAILED\n"
        f"Step: {step}\n"
        f"Step Function: {step_func}\n"
        f"Step Function Arguments: {step_func_args}\n"
        f"Exception Raised: {exception}\n"
        f"<<<STEP FAILED\n"
    )


# Fixtures.
@pytest.fixture
async def clean_user_and_workspace_dbs(asession: AsyncSession) -> None:
    """Delete all entries from `UserWorkspaceDB`, `UserDB`, and `WorkspaceDB` and reset
    the autoincrement counters.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    """

    # Delete from the association table first due to foreign key constraints.
    await asession.execute(delete(UserWorkspaceDB))

    # Delete users and workspaces after the association table is cleared.
    await asession.execute(delete(UserDB))
    await asession.execute(delete(WorkspaceDB))

    # Reset auto-increment sequences.
    await asession.execute(text("ALTER SEQUENCE user_user_id_seq RESTART WITH 1"))
    await asession.execute(
        text("ALTER SEQUENCE workspace_workspace_id_seq RESTART WITH 1")
    )

    await asession.commit()

    # Sanity check.
    assert not await check_if_users_exist(asession=asession)
    assert not await check_if_workspaces_exist(asession=asession)


@pytest.fixture
async def setup_multiple_workspaces(  # pylint: disable=R0915
    asession: AsyncSession,
    clean_user_and_workspace_dbs: pytest.FixtureRequest,
    client: TestClient,
) -> dict[str, dict[str, Any]]:
    """Setup admin and read-only users in multiple workspaces. In addition, log each
    user into their respective workspaces so that there is an access token for each
    user.

    This fixtures sets up the following users and workspaces:

    1. Suzin (Admin) in workspace Suzin.
    2. Mark (Read-Only) in workspace Suzin.
    3. Carlos (Admin) in workspace Carlos.
    4. Zia (Read-Only) in workspace Carlos.
    5. Amir (Admin) in workspace Amir.
    6. Poornima (Admin) in workspace Amir.
    7. Sid (Read-Only) in workspace Amir.
    8. Poornima (Admin) in workspace Suzin.

    NB: Suzin is all powerful since she is the very first admin user. She creates all
    the workspaces for the other admin users as well. Don't mess with Suzin.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    clean_user_and_workspace_dbs
        Fixture to clean the user and workspace databases.
    client
        Test client for the FastAPI application.

    Returns
    -------
    dict[str, dict[str, Any]
        A dictionary containing the response objects for the different users.
    """

    user_workspace_responses: dict[str, dict[str, Any]] = defaultdict(dict)

    # Create Suzin as the (very first) admin user in workspace Suzin.
    response = client.get("/user/require-register")
    json_response = response.json()
    assert json_response["require_register"] is True
    register_suzin_response = client.post(
        "/user/register-first-user",
        json={
            "password": "123",
            "role": UserRoles.ADMIN,
            "username": "Suzin",
            "workspace_name": "Workspace_Suzin",
        },
    )
    suzin_login_response = client.post(
        "/login", data={"username": "Suzin", "password": "123"}
    )
    suzin_access_token = suzin_login_response.json()["access_token"]
    suzin_user_db = await get_user_by_username(asession=asession, username="Suzin")
    suzin_user_id = suzin_user_db.user_id
    suzin_workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name="Workspace_Suzin"
    )
    suzin_workspace_id = suzin_workspace_db.workspace_id
    user_workspace_responses["suzin"] = {
        **register_suzin_response.json(),
        "access_token": suzin_access_token,
        "user_id": suzin_user_id,
        "workspace_name_to_id": {"Workspace_Suzin": suzin_workspace_id},
    }

    # Add Mark as a read only user in workspace Suzin.
    add_mark_response = client.post(
        "/user/",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={
            "password": "123",
            "role": UserRoles.READ_ONLY,
            "username": "Mark",
            "workspace_name": "Workspace_Suzin",
        },
    )
    mark_login_response = client.post(
        "/login", data={"username": "Mark", "password": "123"}
    )
    mark_access_token = mark_login_response.json()["access_token"]
    mark_user_db = await get_user_by_username(asession=asession, username="Mark")
    mark_user_id = mark_user_db.user_id
    user_workspace_responses["mark"] = {
        **add_mark_response.json(),
        "access_token": mark_access_token,
        "user_id": mark_user_id,
        "workspace_name_to_id": {"Workspace_Suzin": suzin_workspace_id},
    }

    # Create workspace Carlos.
    client.post(
        "/workspace/",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={"workspace_name": "Workspace_Carlos"},
    )

    # Add Carlos as the first user in workspace Carlos with an admin role.
    add_carlos_response = client.post(
        "/user/",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={
            "password": "123",
            "role": UserRoles.ADMIN,
            "username": "Carlos",
            "workspace_name": "Workspace_Carlos",
        },
    )
    carlos_login_response = client.post(
        "/login", data={"username": "Carlos", "password": "123"}
    )
    carlos_access_token = carlos_login_response.json()["access_token"]
    carlos_user_db = await get_user_by_username(asession=asession, username="Carlos")
    carlos_user_id = carlos_user_db.user_id
    carlos_workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name="Workspace_Carlos"
    )
    carlos_workspace_id = carlos_workspace_db.workspace_id
    user_workspace_responses["carlos"] = {
        **add_carlos_response.json(),
        "access_token": carlos_access_token,
        "user_id": carlos_user_id,
        "workspace_name_to_id": {"Workspace_Carlos": carlos_workspace_id},
    }

    # Add Zia as a read only user in workspace Carlos.
    add_zia_response = client.post(
        "/user/",
        headers={"Authorization": f"Bearer {carlos_access_token}"},
        json={
            "password": "123",
            "role": UserRoles.READ_ONLY,
            "username": "Zia",
            "workspace_name": "Workspace_Carlos",
        },
    )
    zia_login_response = client.post(
        "/login", data={"username": "Zia", "password": "123"}
    )
    zia_access_token = zia_login_response.json()["access_token"]
    zia_user_db = await get_user_by_username(asession=asession, username="Zia")
    zia_user_id = zia_user_db.user_id
    user_workspace_responses["zia"] = {
        **add_zia_response.json(),
        "access_token": zia_access_token,
        "user_id": zia_user_id,
        "workspace_name_to_id": {"Workspace_Carlos": carlos_workspace_id},
    }

    # Create workspace Amir.
    client.post(
        "/workspace/",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={"workspace_name": "Workspace_Amir"},
    )

    # Add Amir as an admin user in workspace Amir.
    add_amir_response = client.post(
        "/user/",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={
            "password": "123",
            "role": UserRoles.ADMIN,
            "username": "Amir",
            "workspace_name": "Workspace_Amir",
        },
    )
    amir_login_response = client.post(
        "/login", data={"username": "Amir", "password": "123"}
    )
    amir_access_token = amir_login_response.json()["access_token"]
    amir_user_db = await get_user_by_username(asession=asession, username="Amir")
    amir_user_id = amir_user_db.user_id
    amir_workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name="Workspace_Amir"
    )
    amir_workspace_id = amir_workspace_db.workspace_id
    user_workspace_responses["amir"] = {
        **add_amir_response.json(),
        "access_token": amir_access_token,
        "user_id": amir_user_id,
        "workspace_name_to_id": {"Workspace_Amir": amir_workspace_id},
    }

    # Add Poornima as an admin user in workspace Amir.
    add_poornima_response = client.post(
        "/user/",
        headers={"Authorization": f"Bearer {amir_access_token}"},
        json={
            "password": "123",
            "role": UserRoles.ADMIN,
            "username": "Poornima",
            "workspace_name": "Workspace_Amir",
        },
    )
    poornima_login_response = client.post(
        "/login", data={"username": "Poornima", "password": "123"}
    )
    poornima_access_token = poornima_login_response.json()["access_token"]
    poornima_user_db = await get_user_by_username(
        asession=asession, username="Poornima"
    )
    poornima_user_id = poornima_user_db.user_id
    user_workspace_responses["poornima"] = {
        **add_poornima_response.json(),
        "access_token": poornima_access_token,
        "user_id": poornima_user_id,
        "workspace_name_to_id": {"Workspace_Amir": amir_workspace_id},
    }

    # Add Sid as a read-only user in workspace Amir.
    add_sid_response = client.post(
        "/user/",
        headers={"Authorization": f"Bearer {amir_access_token}"},
        json={
            "password": "123",
            "role": UserRoles.READ_ONLY,
            "username": "Sid",
            "workspace_name": "Workspace_Amir",
        },
    )
    sid_login_response = client.post(
        "/login", data={"username": "Sid", "password": "123"}
    )
    sid_access_token = sid_login_response.json()["access_token"]
    sid_user_db = await get_user_by_username(asession=asession, username="Sid")
    sid_user_id = sid_user_db.user_id
    user_workspace_responses["sid"] = {
        **add_sid_response.json(),
        "access_token": sid_access_token,
        "user_id": sid_user_id,
        "workspace_name_to_id": {"Workspace_Amir": amir_workspace_id},
    }

    # Add Poornima as an admin user in workspace Suzin (but do NOT switch Poornima into
    # Suzin's workspace).
    client.post(
        "/user/add-existing-user-to-workspace",
        headers={"Authorization": f"Bearer {suzin_access_token}"},
        json={
            "role": UserRoles.ADMIN,
            "username": "Poornima",
            "workspace_name": "Workspace_Suzin",
        },
    )
    user_workspace_responses["poornima"]["workspace_name_to_id"][
        "Workspace_Suzin"
    ] = suzin_workspace_id

    return user_workspace_responses
