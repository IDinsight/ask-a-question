"""Unit tests for `app.workspaces.service`.

No database or network: every repository function the service calls is replaced
with an `AsyncMock` on the `app.workspaces.service` module, and the session is a
`MagicMock` specced on `AsyncSession` (so `add` is sync and `flush` is async).
"""

from datetime import datetime, timezone
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import JWT_ALGORITHM, JWT_SECRET
from app.core.exceptions import (
    BadRequestError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
)
from app.users.models import UserDB
from app.users.repository import UserNotFoundError
from app.users.schemas import UserRoles
from app.workspaces import service
from app.workspaces.models import WorkspaceDB
from app.workspaces.repository import WorkspaceNotFoundError
from app.workspaces.schemas import WorkspaceCreate, WorkspaceUpdate

NOW = datetime.now(timezone.utc)

PatchRepo = Callable[..., dict[str, AsyncMock]]


def make_user_db(user_id: int = 1, username: str = "caller") -> UserDB:
    """Build a transient `UserDB` (never added to a session).

    Parameters
    ----------
    user_id
        The user ID.
    username
        The username.

    Returns
    -------
    UserDB
        The user object.
    """

    return UserDB(user_id=user_id, username=username)


def make_workspace_db(
    workspace_id: int = 10,
    name: str = "ws",
    doc_language: str = "ENGLISH",
    api_daily_quota: int | None = 100,
) -> WorkspaceDB:
    """Build a transient `WorkspaceDB` (never added to a session).

    Parameters
    ----------
    workspace_id
        The workspace ID.
    name
        The workspace name.
    doc_language
        The workspace document language.
    api_daily_quota
        The workspace's daily API quota.

    Returns
    -------
    WorkspaceDB
        The workspace object.
    """

    return WorkspaceDB(
        api_daily_quota=api_daily_quota,
        content_quota=50,
        created_datetime_utc=NOW,
        doc_language=doc_language,
        updated_datetime_utc=NOW,
        workspace_id=workspace_id,
        workspace_name=name,
    )


@pytest.fixture
def asession() -> MagicMock:
    """Return a fake session (no database).

    Returns
    -------
    MagicMock
        Mock whose async methods (`flush`, `commit`, ...) are `AsyncMock`s.
    """

    return MagicMock(spec=AsyncSession)


@pytest.fixture
def patch_repo(monkeypatch: pytest.MonkeyPatch) -> PatchRepo:
    """Replace functions on `app.workspaces.service` with `AsyncMock`s.

    Keyword values that are already mocks are used as-is (e.g. to set a
    `side_effect`); any other value becomes the mock's `return_value`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    PatchRepo
        Callable `(**name_to_value) -> dict[name, AsyncMock]`.
    """

    def _patch(**values: Any) -> dict[str, AsyncMock]:
        mocks: dict[str, AsyncMock] = {}
        for name, value in values.items():
            mock = (
                value if isinstance(value, AsyncMock) else AsyncMock(return_value=value)
            )
            monkeypatch.setattr(service, name, mock)
            mocks[name] = mock
        return mocks

    return _patch


def test_convert_workspace_db_to_schema() -> None:
    """Test that every field is copied into the response model."""

    workspace_db = make_workspace_db()
    workspace_db.api_key_first_characters = "abcde"

    result = service.convert_workspace_db_to_schema(workspace_db=workspace_db)

    assert result.workspace_id == 10
    assert result.workspace_name == "ws"
    assert result.api_key_first_characters == "abcde"
    assert result.content_quota == 50


class TestCreateWorkspaces:
    """Tests for `create_workspaces`."""

    async def test_caller_without_default_workspace(
        self, asession: MagicMock, patch_repo: PatchRepo
    ) -> None:
        """Test that a user with no default workspace cannot create workspaces.

        Parameters
        ----------
        asession
            Fake session.
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(check_if_user_has_default_workspace=False)
        with pytest.raises(ForbiddenError):
            await service.create_workspaces(
                asession=asession,
                calling_user_db=make_user_db(),
                workspaces=WorkspaceCreate(workspace_name="ws"),
            )

    async def test_only_new_workspaces_returned(
        self, asession: MagicMock, patch_repo: PatchRepo
    ) -> None:
        """Test that new workspaces get the caller as (non-default) admin and are
        returned, while existing ones are silently skipped.

        Parameters
        ----------
        asession
            Fake session.
        patch_repo
            Fixture that patches service dependencies.
        """

        new_db, existing_db = make_workspace_db(1, "new"), make_workspace_db(2, "old")
        mocks = patch_repo(
            add_existing_user_to_workspace=None,
            check_if_user_has_default_workspace=True,
            create_workspace=AsyncMock(
                side_effect=[(new_db, True), (existing_db, False)]
            ),
        )

        result = await service.create_workspaces(
            asession=asession,
            calling_user_db=make_user_db(),
            workspaces=[
                WorkspaceCreate(workspace_name="new"),
                WorkspaceCreate(workspace_name="old"),
            ],
        )

        assert [w.workspace_name for w in result] == ["new"]
        mocks["add_existing_user_to_workspace"].assert_awaited_once()
        assert mocks["add_existing_user_to_workspace"].await_args is not None
        added_user = mocks["add_existing_user_to_workspace"].await_args.kwargs["user"]
        assert added_user.is_default_workspace is False
        assert added_user.role == UserRoles.ADMIN


class TestRetrieveWorkspaces:
    """Tests for the workspace retrieval functions."""

    @pytest.mark.parametrize(
        "call",
        [
            lambda s, u: service.retrieve_admin_workspaces(
                asession=s, calling_user_db=u
            ),
            lambda s, u: service.retrieve_admin_workspace_by_id(
                asession=s, calling_user_db=u, workspace_id=1
            ),
            lambda s, u: service.retrieve_user_workspaces_for_admin(
                asession=s, calling_user_db=u, user_id=2
            ),
        ],
        ids=["all", "by-id", "by-user"],
    )
    async def test_non_admin_forbidden(
        self, asession: MagicMock, call: Callable, patch_repo: PatchRepo
    ) -> None:
        """Test that users who are not an admin anywhere are rejected.

        Parameters
        ----------
        asession
            Fake session.
        call
            Builds the service coroutine to await.
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(user_has_admin_role_in_any_workspace=False)
        with pytest.raises(ForbiddenError):
            await call(asession, make_user_db())

    async def test_retrieve_admin_workspaces(
        self, asession: MagicMock, patch_repo: PatchRepo
    ) -> None:
        """Test that the caller's admin workspaces are returned.

        Parameters
        ----------
        asession
            Fake session.
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            get_workspaces_by_user_role=[
                make_workspace_db(1, "a"),
                make_workspace_db(2),
            ],
            user_has_admin_role_in_any_workspace=True,
        )
        result = await service.retrieve_admin_workspaces(
            asession=asession, calling_user_db=make_user_db()
        )
        assert [w.workspace_id for w in result] == [1, 2]

    async def test_retrieve_workspace_by_name(
        self, asession: MagicMock, patch_repo: PatchRepo
    ) -> None:
        """Test retrieving the current workspace by name.

        Parameters
        ----------
        asession
            Fake session.
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(get_workspace_by_workspace_name=make_workspace_db())
        result = await service.retrieve_workspace_by_name(
            asession=asession, workspace_name="ws"
        )
        assert result.workspace_name == "ws"

    @pytest.mark.parametrize("workspace_id, allowed", [(1, True), (99, False)])
    async def test_retrieve_admin_workspace_by_id(
        self,
        allowed: bool,
        asession: MagicMock,
        patch_repo: PatchRepo,
        workspace_id: int,
    ) -> None:
        """Test that only workspaces the caller administers are returned.

        Parameters
        ----------
        allowed
            Whether the caller is an admin of `workspace_id`.
        asession
            Fake session.
        patch_repo
            Fixture that patches service dependencies.
        workspace_id
            The workspace requested.
        """

        patch_repo(
            get_workspaces_by_user_role=[make_workspace_db(1, "a")],
            user_has_admin_role_in_any_workspace=True,
        )
        call = service.retrieve_admin_workspace_by_id(
            asession=asession, calling_user_db=make_user_db(), workspace_id=workspace_id
        )
        if allowed:
            assert (await call).workspace_id == workspace_id
        else:
            with pytest.raises(ForbiddenError):
                await call

    async def test_retrieve_user_workspaces_unknown_user(
        self, asession: MagicMock, patch_repo: PatchRepo
    ) -> None:
        """Test that an unknown user ID is a 404.

        Parameters
        ----------
        asession
            Fake session.
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            get_user_by_id=AsyncMock(side_effect=UserNotFoundError()),
            user_has_admin_role_in_any_workspace=True,
        )
        with pytest.raises(NotFoundError):
            await service.retrieve_user_workspaces_for_admin(
                asession=asession, calling_user_db=make_user_db(), user_id=2
            )

    @pytest.mark.parametrize(
        "user_workspace_ids, expected_ids",
        [([1, 2, 3], [1, 3]), ([2], None)],
    )
    async def test_retrieve_user_workspaces_for_admin(
        self,
        asession: MagicMock,
        expected_ids: list[int] | None,
        patch_repo: PatchRepo,
        user_workspace_ids: list[int],
    ) -> None:
        """Test that only shared workspaces administered by the caller are returned
        and that having none in common is forbidden.

        Parameters
        ----------
        asession
            Fake session.
        expected_ids
            Workspace IDs expected in the result, or `None` for 403.
        patch_repo
            Fixture that patches service dependencies.
        user_workspace_ids
            IDs of the target user's workspaces.
        """

        patch_repo(
            get_user_by_id=make_user_db(2),
            get_user_workspaces=[make_workspace_db(i) for i in user_workspace_ids],
            # The caller administers workspaces 1 and 3.
            get_workspaces_by_user_role=[make_workspace_db(1), make_workspace_db(3)],
            user_has_admin_role_in_any_workspace=True,
        )
        call = service.retrieve_user_workspaces_for_admin(
            asession=asession, calling_user_db=make_user_db(), user_id=2
        )
        if expected_ids is None:
            with pytest.raises(ForbiddenError):
                await call
        else:
            assert [w.workspace_id for w in await call] == expected_ids


class TestRotateWorkspaceApiKey:
    """Tests for `rotate_workspace_api_key`."""

    async def test_non_admin_forbidden(
        self, asession: MagicMock, patch_repo: PatchRepo
    ) -> None:
        """Test that only admins of the workspace can rotate its key.

        Parameters
        ----------
        asession
            Fake session.
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            get_user_role_in_workspace=UserRoles.READ_ONLY,
            get_workspace_by_workspace_name=make_workspace_db(),
        )
        with pytest.raises(ForbiddenError):
            await service.rotate_workspace_api_key(
                asession=asession, calling_user_db=make_user_db(), workspace_name="ws"
            )

    @pytest.mark.parametrize("db_error", [False, True])
    async def test_rotate(
        self,
        asession: MagicMock,
        db_error: bool,
        monkeypatch: pytest.MonkeyPatch,
        patch_repo: PatchRepo,
    ) -> None:
        """Test that a new key is generated and stored, and that database errors
        become a 500.

        Parameters
        ----------
        asession
            Fake session.
        db_error
            Whether storing the key fails.
        monkeypatch
            Pytest monkeypatch fixture.
        patch_repo
            Fixture that patches service dependencies.
        """

        workspace_db = make_workspace_db()
        monkeypatch.setattr(service, "generate_key", lambda: "fresh-key")
        mocks = patch_repo(
            get_user_role_in_workspace=UserRoles.ADMIN,
            get_workspace_by_workspace_name=workspace_db,
            update_workspace_api_key=AsyncMock(
                return_value=workspace_db,
                side_effect=SQLAlchemyError("boom") if db_error else None,
            ),
        )

        call = service.rotate_workspace_api_key(
            asession=asession, calling_user_db=make_user_db(), workspace_name="ws"
        )
        if db_error:
            with pytest.raises(InternalServerError):
                await call
        else:
            result = await call
            assert result.new_api_key == "fresh-key"
            assert result.workspace_name == "ws"
            assert mocks["update_workspace_api_key"].await_args is not None
            update_kwargs = mocks["update_workspace_api_key"].await_args.kwargs
            assert update_kwargs["new_api_key"] == "fresh-key"
        asession.add.assert_called_once_with(workspace_db)


class TestSwitchUserWorkspace:
    """Tests for `switch_user_workspace`."""

    @pytest.mark.parametrize(
        "target, role, expected",
        [
            ("missing", UserRoles.ADMIN, BadRequestError),
            ("ws", None, InternalServerError),
        ],
    )
    async def test_errors(
        self,
        asession: MagicMock,
        expected: type[Exception],
        patch_repo: PatchRepo,
        role: UserRoles | None,
        target: str,
    ) -> None:
        """Test an unknown workspace and a missing role.

        Parameters
        ----------
        asession
            Fake session.
        expected
            The domain error the service should raise.
        patch_repo
            Fixture that patches service dependencies.
        role
            The role returned by the repository.
        target
            The workspace to switch into.
        """

        patch_repo(
            get_user_role_in_workspace=role, get_user_workspaces=[make_workspace_db()]
        )
        with pytest.raises(expected):
            await service.switch_user_workspace(
                asession=asession, calling_user_db=make_user_db(), workspace_name=target
            )

    async def test_switch(self, asession: MagicMock, patch_repo: PatchRepo) -> None:
        """Test that a token scoped to the new workspace is issued.

        Parameters
        ----------
        asession
            Fake session.
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            get_user_role_in_workspace=UserRoles.READ_ONLY,
            get_user_workspaces=[make_workspace_db(1, "a"), make_workspace_db(2, "b")],
        )
        result = await service.switch_user_workspace(
            asession=asession, calling_user_db=make_user_db(), workspace_name="b"
        )
        assert result.workspace_name == "b"
        assert result.user_role == UserRoles.READ_ONLY
        payload = jwt.decode(
            result.access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        assert payload["workspace_name"] == "b"
        assert payload["username"] == "caller"


class TestUpdateWorkspace:
    """Tests for `update_workspace` and `check_update_workspace_call`."""

    @pytest.mark.parametrize("returns_new_object", [False, True])
    async def test_update_workspace(
        self, asession: MagicMock, patch_repo: PatchRepo, returns_new_object: bool
    ) -> None:
        """Test the response built from the checked and updated records.

        The repository normally mutates and returns the same object; a distinct
        object exercises the "value changed" branches.

        Parameters
        ----------
        asession
            Fake session.
        patch_repo
            Fixture that patches service dependencies.
        returns_new_object
            Whether the repository returns a different object with new values.
        """

        checked_db = make_workspace_db()
        updated_db = (
            make_workspace_db(name="renamed", doc_language="FRENCH", api_daily_quota=5)
            if returns_new_object
            else checked_db
        )
        patch_repo(
            check_update_workspace_call=checked_db,
            update_workspace_attrs=updated_db,
        )

        result = await service.update_workspace(
            asession=asession,
            calling_user_db=make_user_db(),
            workspace=WorkspaceUpdate(workspace_name="renamed"),
            workspace_id=10,
        )

        assert result.workspace_name == updated_db.workspace_name
        assert result.doc_language == updated_db.doc_language
        assert result.api_daily_quota == updated_db.api_daily_quota

    async def test_update_workspace_db_error(
        self, asession: MagicMock, patch_repo: PatchRepo
    ) -> None:
        """Test that database errors become a 500.

        Parameters
        ----------
        asession
            Fake session.
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            check_update_workspace_call=make_workspace_db(),
            update_workspace_attrs=AsyncMock(side_effect=SQLAlchemyError("boom")),
        )
        with pytest.raises(InternalServerError):
            await service.update_workspace(
                asession=asession,
                calling_user_db=make_user_db(),
                workspace=WorkspaceUpdate(),
                workspace_id=10,
            )

    @pytest.fixture
    def happy_path(self, patch_repo: PatchRepo) -> dict[str, AsyncMock]:
        """Patch every dependency so that `check_update_workspace_call` passes.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.

        Returns
        -------
        dict[str, AsyncMock]
            The mocks, so individual tests can override one of them.
        """

        return patch_repo(
            get_user_role_in_workspace=UserRoles.ADMIN,
            get_workspace_by_workspace_id=make_workspace_db(),
            is_workspace_name_valid=True,
        )

    @pytest.mark.parametrize(
        "workspace, override, expected",
        [
            (
                WorkspaceUpdate(
                    api_daily_quota=-1, content_quota=-1, doc_language="KLINGON"
                ),
                {},
                BadRequestError,
            ),
            (
                WorkspaceUpdate(),
                {
                    "get_workspace_by_workspace_id": AsyncMock(
                        side_effect=WorkspaceNotFoundError()
                    )
                },
                NotFoundError,
            ),
            (
                WorkspaceUpdate(workspace_name="taken"),
                {"is_workspace_name_valid": False},
                BadRequestError,
            ),
            (
                WorkspaceUpdate(),
                {"get_user_role_in_workspace": UserRoles.READ_ONLY},
                ForbiddenError,
            ),
        ],
        ids=["no-valid-updates", "unknown-workspace", "name-taken", "not-admin"],
    )
    async def test_check_update_workspace_call_errors(
        self,
        asession: MagicMock,
        expected: type[Exception],
        happy_path: dict[str, AsyncMock],
        override: dict[str, Any],
        patch_repo: PatchRepo,
        workspace: WorkspaceUpdate,
    ) -> None:
        """Test each rejection branch.

        Parameters
        ----------
        asession
            Fake session.
        expected
            The domain error the service should raise.
        happy_path
            Mocks that make the check pass (overridden per case).
        override
            Dependencies to change for this case.
        patch_repo
            Fixture that patches service dependencies.
        workspace
            The update payload.
        """

        patch_repo(**override)
        with pytest.raises(expected):
            await service.check_update_workspace_call(
                asession=asession,
                calling_user_db=make_user_db(),
                workspace=workspace,
                workspace_id=10,
            )

    @pytest.mark.parametrize("workspace_name", [None, "ws", "brand_new"])
    async def test_check_update_workspace_call_allowed(
        self,
        asession: MagicMock,
        happy_path: dict[str, AsyncMock],
        workspace_name: str | None,
    ) -> None:
        """Test that valid updates (no rename, same name, free name) pass and that
        the name is only checked for uniqueness when it actually changes.

        Parameters
        ----------
        asession
            Fake session.
        happy_path
            Mocks that make the check pass.
        workspace_name
            The requested workspace name.
        """

        result = await service.check_update_workspace_call(
            asession=asession,
            calling_user_db=make_user_db(),
            workspace=WorkspaceUpdate(workspace_name=workspace_name),
            workspace_id=10,
        )
        assert result.workspace_id == 10
        expected_checks = 1 if workspace_name == "brand_new" else 0
        assert happy_path["is_workspace_name_valid"].await_count == expected_checks
