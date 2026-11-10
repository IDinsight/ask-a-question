"""Tests for `app.workspaces.repository`.

Every test runs against the real database through `rollback_asession`, so rows are
created per test and discarded on teardown (no clean-up code needed).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_key_hash
from app.users.schemas import UserCreate
from app.workspaces.repository import (
    WorkspaceNotFoundError,
    check_if_workspaces_exist,
    create_workspace,
    get_content_quota_by_workspace_id,
    get_workspace_by_workspace_id,
    get_workspace_by_workspace_name,
    is_workspace_name_valid,
    update_workspace_api_key,
    update_workspace_attrs,
)
from app.workspaces.schemas import WorkspaceUpdate
from tests.workspaces.conftest import MakeWorkspace, unique_name


class TestCreateWorkspace:
    """Tests for `create_workspace` and `check_if_workspaces_exist`."""

    async def test_create_new_then_existing(
        self, rollback_asession: AsyncSession
    ) -> None:
        """Test that a workspace is created once and then returned as existing.

        Parameters
        ----------
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user = UserCreate(username="creator", workspace_name=unique_name("created"))

        workspace_db, is_new = await create_workspace(
            api_daily_quota=10,
            asession=rollback_asession,
            content_quota=5,
            doc_language="ENGLISH",
            user=user,
        )
        assert is_new is True
        assert workspace_db.workspace_name == user.workspace_name
        assert (workspace_db.api_daily_quota, workspace_db.content_quota) == (10, 5)
        assert await check_if_workspaces_exist(asession=rollback_asession) is True

        again_db, is_new = await create_workspace(
            asession=rollback_asession, doc_language="ENGLISH", user=user
        )
        assert is_new is False
        assert again_db.workspace_id == workspace_db.workspace_id


class TestGetWorkspace:
    """Tests for the workspace lookup functions."""

    async def test_lookups(
        self, make_workspace: MakeWorkspace, rollback_asession: AsyncSession
    ) -> None:
        """Test looking a workspace up by ID and by name, and its content quota.

        Parameters
        ----------
        make_workspace
            Factory that inserts a workspace.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        workspace_db = await make_workspace(content_quota=7)

        by_id = await get_workspace_by_workspace_id(
            asession=rollback_asession, workspace_id=workspace_db.workspace_id
        )
        by_name = await get_workspace_by_workspace_name(
            asession=rollback_asession, workspace_name=workspace_db.workspace_name
        )
        quota = await get_content_quota_by_workspace_id(
            asession=rollback_asession, workspace_id=workspace_db.workspace_id
        )

        assert by_id.workspace_id == by_name.workspace_id == workspace_db.workspace_id
        assert quota == 7
        assert not await is_workspace_name_valid(
            asession=rollback_asession, workspace_name=workspace_db.workspace_name
        )
        assert await is_workspace_name_valid(
            asession=rollback_asession, workspace_name="no_such_workspace"
        )

    @pytest.mark.parametrize(
        "lookup, kwargs",
        [
            (get_workspace_by_workspace_id, {"workspace_id": -1}),
            (get_workspace_by_workspace_name, {"workspace_name": "no_such_workspace"}),
            (get_content_quota_by_workspace_id, {"workspace_id": -1}),
        ],
    )
    async def test_lookup_not_found(
        self,
        kwargs: dict[str, int | str],
        lookup: object,
        rollback_asession: AsyncSession,
    ) -> None:
        """Test that each lookup raises `WorkspaceNotFoundError` for unknown keys.

        Parameters
        ----------
        kwargs
            Keyword arguments identifying a workspace that does not exist.
        lookup
            The repository function under test.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        with pytest.raises(WorkspaceNotFoundError):
            await lookup(asession=rollback_asession, **kwargs)  # type: ignore[operator]


class TestUpdateWorkspace:
    """Tests for the workspace update functions."""

    async def test_update_workspace_api_key(
        self, make_workspace: MakeWorkspace, rollback_asession: AsyncSession
    ) -> None:
        """Test updating the API key for a workspace.

        Parameters
        ----------
        make_workspace
            Factory that inserts a workspace.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        workspace_db = await make_workspace()
        updated_workspace_db = await update_workspace_api_key(
            asession=rollback_asession,
            new_api_key="new_key",  # pragma: allowlist secret
            workspace_db=workspace_db,
        )
        assert updated_workspace_db.hashed_api_key == get_key_hash(key="new_key")
        assert updated_workspace_db.api_key_first_characters == "new_k"
        assert updated_workspace_db.api_key_updated_datetime_utc is not None

    @pytest.mark.parametrize(
        "doc_language, rename, expected_language",
        [("FRENCH", True, "FRENCH"), ("NOT_A_LANGUAGE", False, "ENGLISH")],
    )
    async def test_update_workspace_attrs(
        self,
        doc_language: str,
        expected_language: str,
        make_workspace: MakeWorkspace,
        rename: bool,
        rollback_asession: AsyncSession,
    ) -> None:
        """Test that only supported languages and non-null names are applied.

        Parameters
        ----------
        doc_language
            Requested document language.
        expected_language
            Language stored after the update.
        make_workspace
            Factory that inserts a workspace.
        rename
            Whether a new workspace name is supplied.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        workspace_db = await make_workspace()
        original_name = workspace_db.workspace_name
        new_name = unique_name("renamed") if rename else None

        updated = await update_workspace_attrs(
            asession=rollback_asession,
            workspace=WorkspaceUpdate(
                doc_language=doc_language, workspace_name=new_name
            ),
            workspace_db=workspace_db,
        )

        assert updated.doc_language == expected_language
        assert updated.workspace_name == (new_name or original_name)
