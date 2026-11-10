"""Fixtures shared by the users tests."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_salted_hash
from app.users.models import UserDB, UserWorkspaceDB
from app.users.schemas import UserRoles
from app.workspaces.models import WorkspaceDB
from tests.conftest import TEST_WORKSPACE_NAME_1

NEW_USER_PASSWORD = "new_user_password"  # pragma: allowlist secret

MakeUser = Callable[..., Awaitable[UserDB]]
MakeWorkspace = Callable[..., Awaitable[WorkspaceDB]]
AddToWorkspace = Callable[..., Awaitable[UserWorkspaceDB]]


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
def make_user(rollback_asession: AsyncSession) -> MakeUser:
    """Factory that inserts a `UserDB` row into the rolled-back session.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.

    Returns
    -------
    MakeUser
        Async callable `(username=None, password=..., recovery_codes=None) -> UserDB`.
    """

    async def _make_user(
        *,
        username: str | None = None,
        password: str = NEW_USER_PASSWORD,
        recovery_codes: list[str] | None = None,
    ) -> UserDB:
        now = datetime.now(timezone.utc)
        user_db = UserDB(
            created_datetime_utc=now,
            hashed_password=get_password_salted_hash(key=password),
            recovery_codes=recovery_codes,
            updated_datetime_utc=now,
            username=username or unique_name("repo_user"),
        )
        rollback_asession.add(user_db)
        await rollback_asession.flush()
        return user_db

    return _make_user


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
        Async callable `(workspace_name=None) -> WorkspaceDB`.
    """

    async def _make_workspace(*, workspace_name: str | None = None) -> WorkspaceDB:
        now = datetime.now(timezone.utc)
        workspace_db = WorkspaceDB(
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
def add_to_workspace(rollback_asession: AsyncSession) -> AddToWorkspace:
    """Factory that assigns a user to a workspace in the rolled-back session.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.

    Returns
    -------
    AddToWorkspace
        Async callable `(user_db, workspace_db, role=ADMIN, default=False,
        created_offset_s=0) -> UserWorkspaceDB`. `created_offset_s` shifts the
        created timestamp so tests can control "earliest workspace" ordering.
    """

    async def _add_to_workspace(
        user_db: UserDB,
        workspace_db: WorkspaceDB,
        *,
        role: UserRoles = UserRoles.ADMIN,
        default: bool = False,
        created_offset_s: int = 0,
    ) -> UserWorkspaceDB:
        now = datetime.now(timezone.utc)
        user_workspace_db = UserWorkspaceDB(
            created_datetime_utc=now + timedelta(seconds=created_offset_s),
            default_workspace=default,
            updated_datetime_utc=now,
            user_id=user_db.user_id,
            user_role=role,
            workspace_id=workspace_db.workspace_id,
        )
        rollback_asession.add(user_workspace_db)
        await rollback_asession.flush()
        return user_workspace_db

    return _add_to_workspace


@pytest.fixture
def new_user_in_workspace_1(
    access_token_admin_1: str, client: TestClient
) -> dict[str, Any]:
    """Create a fresh read-only user in workspace 1 through the API.

    Tests that change a user's password, name or recovery codes use this fixture so
    the session-wide users from `tests/conftest.py` are never modified.

    Parameters
    ----------
    access_token_admin_1
        Admin access token in workspace 1.
    client
        Test client.

    Returns
    -------
    dict[str, Any]
        The `/user/` response body (username, recovery codes, role, workspace) plus
        the new user's `user_id`.
    """

    headers = {"Authorization": f"Bearer {access_token_admin_1}"}
    response = client.post(
        "/user/",
        headers=headers,
        json={
            "is_default_workspace": True,
            "password": NEW_USER_PASSWORD,
            "role": UserRoles.READ_ONLY,
            "username": unique_name("router_user"),
            "workspace_name": TEST_WORKSPACE_NAME_1,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    # The create endpoint does not return the ID, so look it up in the user list.
    users = client.get("/user/", headers=headers).json()
    user["user_id"] = next(
        u["user_id"] for u in users if u["username"] == user["username"]
    )
    return user
