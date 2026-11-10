"""Fixtures shared by the workspaces tests."""

import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.users.schemas import UserRoles
from app.workspaces.models import WorkspaceDB
from tests.conftest import TEST_ADMIN_USERNAME_1

MakeWorkspace = Callable[..., Awaitable[WorkspaceDB]]


def unique_name(prefix: str) -> str:
    """Return a name that will not clash with rows created by other tests.

    Parameters
    ----------
    prefix
        Human-readable prefix for the name.

    Returns
    -------
    str
        The prefix followed by a short random suffix.
    """

    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def make_workspace(rollback_asession: AsyncSession) -> MakeWorkspace:
    """Factory that inserts a `WorkspaceDB` row into the rolled-back session.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.

    Returns
    -------
    MakeWorkspace
        Async callable `(workspace_name=None, content_quota=None) -> WorkspaceDB`.
    """

    async def _make_workspace(
        *, workspace_name: str | None = None, content_quota: int | None = None
    ) -> WorkspaceDB:
        now = datetime.now(timezone.utc)
        workspace_db = WorkspaceDB(
            content_quota=content_quota,
            created_datetime_utc=now,
            doc_language="ENGLISH",
            updated_datetime_utc=now,
            workspace_name=workspace_name or unique_name("repo_workspace"),
        )
        rollback_asession.add(workspace_db)
        await rollback_asession.flush()
        return workspace_db

    return _make_workspace


@pytest.fixture
def temp_workspace(access_token_admin_1: str, client: TestClient) -> dict[str, Any]:
    """Create a fresh workspace (admin 1 becomes its admin) through the API.

    Tests that rename a workspace or rotate its API key use this so the shared
    workspaces and their session-scoped API keys are never touched. Workspaces
    cannot be deleted through the API; the DB is truncated at the next session.

    Parameters
    ----------
    access_token_admin_1
        Admin access token in workspace 1.
    client
        Test client.

    Returns
    -------
    dict[str, Any]
        The created workspace (`WorkspaceRetrieve` JSON) plus `access_token`, an
        admin-1 token scoped to the new workspace.
    """

    workspace_name = unique_name("router_workspace")
    response = client.post(
        "/workspace/",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
        json={"workspace_name": workspace_name},
    )
    assert response.status_code == status.HTTP_200_OK
    (workspace,) = response.json()
    workspace["access_token"] = create_access_token(
        user_role=UserRoles.ADMIN,
        username=TEST_ADMIN_USERNAME_1,
        workspace_name=workspace_name,
    )
    return workspace
