"""Unit tests for `app.users.service`.

No database or network: every repository function the service calls is replaced
with an `AsyncMock` on the `app.users.service` module, and `asession` is a bare
`AsyncMock`.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import AsyncMock

import pytest
import sqlalchemy

from app.core.exceptions import (
    BadRequestError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
)
from app.users import service
from app.users.models import UserDB
from app.users.repository import (
    UserNotFoundError,
    UserNotFoundInWorkspaceError,
    UserWorkspaceRoleAlreadyExistsError,
)
from app.users.schemas import (
    UserCreate,
    UserCreateWithCode,
    UserCreateWithPassword,
    UserResetPassword,
    UserRoles,
    UserUpdate,
)
from app.workspaces.models import WorkspaceDB
from app.workspaces.repository import WorkspaceNotFoundError

NOW = datetime.now(timezone.utc)
PASSWORD = "service_password"  # pragma: allowlist secret

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

    return UserDB(
        created_datetime_utc=NOW,
        recovery_codes=["code_1", "code_2"],
        updated_datetime_utc=NOW,
        user_id=user_id,
        username=username,
    )


def make_workspace_db(workspace_id: int = 10, name: str = "ws") -> WorkspaceDB:
    """Build a transient `WorkspaceDB` (never added to a session).

    Parameters
    ----------
    workspace_id
        The workspace ID.
    name
        The workspace name.

    Returns
    -------
    WorkspaceDB
        The workspace object.
    """

    return WorkspaceDB(
        api_daily_quota=100, workspace_id=workspace_id, workspace_name=name
    )


def role_row(
    workspace_id: int = 10,
    workspace_name: str = "ws",
    default: bool = True,
    role: UserRoles = UserRoles.ADMIN,
) -> SimpleNamespace:
    """Build a row shaped like those from `get_user_role_in_all_workspaces`.

    Parameters
    ----------
    workspace_id
        The workspace ID.
    workspace_name
        The workspace name.
    default
        Whether this is the user's default workspace.
    role
        The user's role in the workspace.

    Returns
    -------
    SimpleNamespace
        Object with the same attributes as the SQLAlchemy row.
    """

    return SimpleNamespace(
        default_workspace=default,
        user_role=role,
        workspace_id=workspace_id,
        workspace_name=workspace_name,
    )


@pytest.fixture
def patch_repo(monkeypatch: pytest.MonkeyPatch) -> PatchRepo:
    """Replace functions on `app.users.service` with `AsyncMock`s.

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


class TestCreateAndAddUser:
    """Tests for `create_user_in_workspace` and `add_user_to_workspace`."""

    async def test_create_user_existing_username(self, patch_repo: PatchRepo) -> None:
        """Test that an existing username is rejected.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(check_if_user_exists=make_user_db())
        with pytest.raises(BadRequestError):
            await service.create_user_in_workspace(
                asession=AsyncMock(),
                calling_user_db=make_user_db(),
                user=UserCreateWithPassword(password=PASSWORD, username="new"),
            )

    async def test_create_user(self, patch_repo: PatchRepo) -> None:
        """Test that a new user is checked and then added to the workspace.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        user = UserCreateWithPassword(
            password=PASSWORD, username="new", workspace_name="ws"
        )
        workspace_db = make_workspace_db()
        expected = UserCreateWithCode(recovery_codes=["c"], username="new")
        mocks = patch_repo(
            add_new_user_to_workspace=expected,
            check_create_or_add_user_call=(user, workspace_db),
            check_if_user_exists=None,
        )

        result = await service.create_user_in_workspace(
            asession=AsyncMock(), calling_user_db=make_user_db(), user=user
        )

        assert result is expected
        assert mocks["add_new_user_to_workspace"].await_args is not None
        assert mocks["add_new_user_to_workspace"].await_args.kwargs["workspace_db"] is (
            workspace_db
        )

    async def test_add_user_unknown_username(self, patch_repo: PatchRepo) -> None:
        """Test that adding a user who does not exist is a 404.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(check_if_user_exists=None)
        with pytest.raises(NotFoundError):
            await service.add_user_to_workspace(
                asession=AsyncMock(),
                calling_user_db=make_user_db(),
                user=UserCreate(username="ghost"),
            )

    @pytest.mark.parametrize("role_exists", [False, True])
    async def test_add_user(self, patch_repo: PatchRepo, role_exists: bool) -> None:
        """Test adding an existing user, including when they already have a role in
        the workspace.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        role_exists
            Whether the repository reports the role as already existing.
        """

        user = UserCreate(username="existing", workspace_name="ws")
        expected = UserCreateWithCode(recovery_codes=[], username="existing")
        add_mock = AsyncMock(
            side_effect=UserWorkspaceRoleAlreadyExistsError("dup")
            if role_exists
            else None,
            return_value=expected,
        )
        patch_repo(
            add_existing_user_to_workspace=add_mock,
            check_create_or_add_user_call=(user, make_workspace_db()),
            check_if_user_exists=make_user_db(),
        )

        if role_exists:
            with pytest.raises(BadRequestError):
                await service.add_user_to_workspace(
                    asession=AsyncMock(), calling_user_db=make_user_db(), user=user
                )
        else:
            result = await service.add_user_to_workspace(
                asession=AsyncMock(), calling_user_db=make_user_db(), user=user
            )
            assert result is expected


class TestRegisterFirstUser:
    """Tests for `register_first_user` and `check_register_required`."""

    async def test_register_when_users_exist(self, patch_repo: PatchRepo) -> None:
        """Test that registration is refused once users and workspaces exist.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(check_if_users_exist=True, check_if_workspaces_exist=True)
        with pytest.raises(BadRequestError):
            await service.register_first_user(
                asession=AsyncMock(),
                redis=AsyncMock(),
                user=UserCreateWithPassword(password=PASSWORD, username="first"),
            )

    async def test_register_first_user(self, patch_repo: PatchRepo) -> None:
        """Test that the first user becomes ADMIN of a default-named workspace and
        that API limits are initialised.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        workspace_db = make_workspace_db(name="first's Workspace")
        expected = UserCreateWithCode(recovery_codes=["c"], username="first")
        mocks = patch_repo(
            add_new_user_to_workspace=expected,
            check_if_users_exist=False,
            check_if_workspaces_exist=False,
            create_workspace=(workspace_db, True),
            update_api_limits=None,
        )
        user = UserCreateWithPassword(
            password=PASSWORD, role=UserRoles.READ_ONLY, username="first"
        )

        result = await service.register_first_user(
            asession=AsyncMock(), redis=AsyncMock(), user=user
        )

        assert result is expected
        # The user object is updated in place.
        assert user.role == UserRoles.ADMIN
        assert user.workspace_name == "first's Workspace"
        assert mocks["update_api_limits"].await_args is not None
        limits_kwargs = mocks["update_api_limits"].await_args.kwargs
        assert limits_kwargs["api_daily_quota"] == workspace_db.api_daily_quota
        assert limits_kwargs["workspace_name"] == workspace_db.workspace_name

    @pytest.mark.parametrize(
        "users_exist, workspaces_exist, expected",
        [(True, True, False), (False, False, True), (True, False, True)],
    )
    async def test_check_register_required(
        self,
        expected: bool,
        patch_repo: PatchRepo,
        users_exist: bool,
        workspaces_exist: bool,
    ) -> None:
        """Test that registration is required unless users AND workspaces exist.

        Parameters
        ----------
        expected
            Expected `require_register` value.
        patch_repo
            Fixture that patches service dependencies.
        users_exist
            Whether users exist.
        workspaces_exist
            Whether workspaces exist.
        """

        patch_repo(
            check_if_users_exist=users_exist, check_if_workspaces_exist=workspaces_exist
        )
        result = await service.check_register_required(asession=AsyncMock())
        assert result.require_register is expected


class TestDeleteUserFromWorkspace:
    """Tests for `delete_user_from_workspace`."""

    @pytest.mark.parametrize(
        "error, expected",
        [
            (UserNotFoundInWorkspaceError("x"), NotFoundError),
            (
                sqlalchemy.exc.IntegrityError("stmt", {}, Exception()),
                InternalServerError,
            ),
        ],
    )
    async def test_repository_errors(
        self, error: Exception, expected: type[Exception], patch_repo: PatchRepo
    ) -> None:
        """Test that repository errors are mapped to domain errors.

        Parameters
        ----------
        error
            The error raised by `remove_user_from_dbs`.
        expected
            The domain error the service should raise.
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            check_remove_user_from_workspace_call=(
                make_workspace_db(),
                make_user_db(2),
            ),
            remove_user_from_dbs=AsyncMock(side_effect=error),
        )
        with pytest.raises(expected):
            await service.delete_user_from_workspace(
                asession=AsyncMock(),
                calling_user_db=make_user_db(1),
                remove_from_workspace_name="ws",
                user_id=2,
                workspace_name="ws",
            )

    @pytest.mark.parametrize(
        "user_id, default_name, current_ws, require_auth, require_switch",
        [
            (2, "other", "ws", False, False),  # Removing someone else.
            (1, None, "ws", True, True),  # Self-removal from the only workspace.
            (1, "other", "ws", False, True),  # Self-removal from current workspace.
            (1, "other", "elsewhere", False, False),  # Self-removal, not current.
        ],
    )
    async def test_response_flags(
        self,
        current_ws: str,
        default_name: str | None,
        patch_repo: PatchRepo,
        require_auth: bool,
        require_switch: bool,
        user_id: int,
    ) -> None:
        """Test the re-authentication / workspace-switch flags in the response.

        Parameters
        ----------
        current_ws
            The workspace the calling user (ID 1) is logged into.
        default_name
            The removed user's default workspace after removal.
        patch_repo
            Fixture that patches service dependencies.
        require_auth
            Expected `require_authentication`.
        require_switch
            Expected `require_workspace_switch`.
        user_id
            The ID of the user being removed.
        """

        patch_repo(
            check_remove_user_from_workspace_call=(
                make_workspace_db(),
                make_user_db(user_id),
            ),
            remove_user_from_dbs=(default_name, "ws"),
        )
        result = await service.delete_user_from_workspace(
            asession=AsyncMock(),
            calling_user_db=make_user_db(1),
            remove_from_workspace_name="ws",
            user_id=user_id,
            workspace_name=current_ws,
        )
        assert result.default_workspace_name == default_name
        assert result.removed_from_workspace_name == "ws"
        assert result.require_authentication is require_auth
        assert result.require_workspace_switch is require_switch


class TestListUsersInWorkspace:
    """Tests for `list_users_in_workspace`."""

    async def test_admin_sees_all_users_grouped(self, patch_repo: PatchRepo) -> None:
        """Test that an admin gets every user, with repeated rows merged per user.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        def row(username: str, user_id: int, default: bool) -> SimpleNamespace:
            return SimpleNamespace(
                created_datetime_utc=NOW,
                default_workspace=default,
                updated_datetime_utc=NOW,
                user_id=user_id,
                user_role=UserRoles.ADMIN,
                username=username,
            )

        patch_repo(
            get_user_role_in_workspace=UserRoles.ADMIN,
            get_users_and_roles_by_workspace_id=[
                row("alice", 1, True),
                row("bob", 2, True),
                row("alice", 1, False),
            ],
            get_workspace_by_workspace_name=make_workspace_db(),
        )

        users = await service.list_users_in_workspace(
            asession=AsyncMock(), calling_user_db=make_user_db(), workspace_name="ws"
        )

        assert [u.username for u in users] == ["alice", "bob"]
        assert users[0].is_default_workspace == [True, False]
        assert len(users[0].user_workspaces) == 2

    async def test_read_only_sees_only_self(self, patch_repo: PatchRepo) -> None:
        """Test that a read-only user only gets their own details.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            get_user_role_in_all_workspaces=[role_row(role=UserRoles.READ_ONLY)],
            get_user_role_in_workspace=UserRoles.READ_ONLY,
            get_workspace_by_workspace_name=make_workspace_db(),
        )
        users = await service.list_users_in_workspace(
            asession=AsyncMock(), calling_user_db=make_user_db(), workspace_name="ws"
        )
        assert [u.username for u in users] == ["caller"]
        assert users[0].user_workspaces[0].user_role == UserRoles.READ_ONLY

    @pytest.mark.parametrize(
        "role, expected", [(None, InternalServerError), ("guest", ForbiddenError)]
    )
    async def test_invalid_role(
        self, expected: type[Exception], patch_repo: PatchRepo, role: str | None
    ) -> None:
        """Test a missing role and an unknown role.

        Parameters
        ----------
        expected
            The domain error the service should raise.
        patch_repo
            Fixture that patches service dependencies.
        role
            The role returned by the repository.
        """

        patch_repo(
            get_user_role_in_workspace=role,
            get_workspace_by_workspace_name=make_workspace_db(),
        )
        with pytest.raises(expected):
            await service.list_users_in_workspace(
                asession=AsyncMock(),
                calling_user_db=make_user_db(),
                workspace_name="ws",
            )


class TestResetPassword:
    """Tests for `reset_user_password` and `check_reset_password_call`."""

    async def test_reset_user_password(self, patch_repo: PatchRepo) -> None:
        """Test that the used recovery code is dropped and the user returned.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        user_db = make_user_db()
        mocks = patch_repo(
            check_if_user_exists=user_db,
            get_user_role_in_all_workspaces=[role_row()],
            reset_user_password_in_db=user_db,
        )

        result = await service.reset_user_password(
            asession=AsyncMock(),
            user=UserResetPassword(
                password=PASSWORD, recovery_code="code_1", username="caller"
            ),
        )

        assert result.username == "caller"
        assert mocks["reset_user_password_in_db"].await_args is not None
        reset_kwargs = mocks["reset_user_password_in_db"].await_args.kwargs
        assert reset_kwargs["recovery_codes"] == ["code_2"]

    @pytest.mark.parametrize(
        "user_db, code, expected",
        [
            (None, "code_1", NotFoundError),
            (make_user_db(), "wrong", BadRequestError),
            (make_user_db(), "", BadRequestError),
        ],
    )
    async def test_check_reset_password_call_errors(
        self,
        code: str,
        expected: type[Exception],
        patch_repo: PatchRepo,
        user_db: UserDB | None,
    ) -> None:
        """Test unknown users and bad recovery codes.

        Parameters
        ----------
        code
            The recovery code supplied.
        expected
            The domain error the service should raise.
        patch_repo
            Fixture that patches service dependencies.
        user_db
            The user returned by `check_if_user_exists`.
        """

        patch_repo(check_if_user_exists=user_db)
        with pytest.raises(expected):
            await service.check_reset_password_call(
                asession=AsyncMock(),
                user=UserResetPassword(
                    password=PASSWORD, recovery_code=code, username="caller"
                ),
            )


class TestUpdateUserDetails:
    """Tests for `update_user_details` and `get_user_details`."""

    @pytest.mark.parametrize(
        "user, role_calls, default_calls",
        [
            (UserUpdate(username="new"), 0, 0),
            (
                UserUpdate(
                    is_default_workspace=True,
                    role=UserRoles.ADMIN,
                    username="new",
                    workspace_name="ws",
                ),
                1,
                1,
            ),
        ],
    )
    async def test_update_user_details(
        self,
        default_calls: int,
        patch_repo: PatchRepo,
        role_calls: int,
        user: UserUpdate,
    ) -> None:
        """Test that role / default workspace updates only happen when requested.

        Parameters
        ----------
        default_calls
            Expected number of default-workspace updates.
        patch_repo
            Fixture that patches service dependencies.
        role_calls
            Expected number of role updates.
        user
            The update payload.
        """

        workspace_db = make_workspace_db() if user.workspace_name else None
        mocks = patch_repo(
            check_update_user_call=(make_user_db(2, "old"), workspace_db),
            get_user_role_in_all_workspaces=[role_row()],
            update_user_default_workspace=None,
            update_user_in_db=make_user_db(2, "new"),
            update_user_role_in_workspace=None,
        )

        result = await service.update_user_details(
            asession=AsyncMock(), calling_user_db=make_user_db(), user=user, user_id=2
        )

        assert result.username == "new"
        assert mocks["update_user_role_in_workspace"].await_count == role_calls
        assert mocks["update_user_default_workspace"].await_count == default_calls

    @pytest.mark.parametrize(
        "failing", ["update_user_role_in_workspace", "update_user_default_workspace"]
    )
    async def test_update_user_not_in_workspace(
        self, failing: str, patch_repo: PatchRepo
    ) -> None:
        """Test that a user missing from the workspace is reported as 404.

        Parameters
        ----------
        failing
            The repository update that raises.
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            check_update_user_call=(make_user_db(2), make_workspace_db()),
            update_user_default_workspace=None,
            update_user_role_in_workspace=None,
        )
        patch_repo(**{failing: AsyncMock(side_effect=UserNotFoundInWorkspaceError())})

        with pytest.raises(NotFoundError):
            await service.update_user_details(
                asession=AsyncMock(),
                calling_user_db=make_user_db(),
                user=UserUpdate(
                    is_default_workspace=True,
                    role=UserRoles.ADMIN,
                    username="x",
                    workspace_name="ws",
                ),
                user_id=2,
            )

    async def test_get_user_details(self, patch_repo: PatchRepo) -> None:
        """Test that the user's workspaces and roles are included.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            get_user_role_in_all_workspaces=[
                role_row(10, "a", True, UserRoles.ADMIN),
                role_row(11, "b", False, UserRoles.READ_ONLY),
            ]
        )
        result = await service.get_user_details(
            asession=AsyncMock(), user_db=make_user_db()
        )
        assert result.is_default_workspace == [True, False]
        assert [w.workspace_name for w in result.user_workspaces] == ["a", "b"]


class TestCheckUsernameExists:
    """Tests for `check_username_exists`."""

    @pytest.mark.parametrize(
        "is_admin, existing, expected",
        [
            (False, None, ForbiddenError),
            (True, None, NotFoundError),
            (True, make_user_db(), None),
        ],
    )
    async def test_check_username_exists(
        self,
        existing: UserDB | None,
        expected: type[Exception] | None,
        is_admin: bool,
        patch_repo: PatchRepo,
    ) -> None:
        """Test the role check and the existence check.

        Parameters
        ----------
        existing
            The user returned by `check_if_user_exists`.
        expected
            The domain error expected, or `None` for success.
        is_admin
            Whether the calling user is an admin anywhere.
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            check_if_user_exists=existing,
            user_has_admin_role_in_any_workspace=is_admin,
        )
        call = service.check_username_exists(
            asession=AsyncMock(), calling_user_db=make_user_db(), username="someone"
        )
        if expected is None:
            # Returns `None`; success means it does not raise.
            await call
        else:
            with pytest.raises(expected):
                await call


class TestCheckRemoveUserFromWorkspaceCall:
    """Tests for `check_remove_user_from_workspace_call`."""

    async def call(self) -> tuple[WorkspaceDB, UserDB]:
        """Invoke the check for user ID 2 being removed from "ws" by user ID 1.

        Returns
        -------
        tuple[WorkspaceDB, UserDB]
            The result of the check.
        """

        return await service.check_remove_user_from_workspace_call(
            asession=AsyncMock(),
            calling_user_db=make_user_db(1),
            remove_from_workspace_name="ws",
            user_id=2,
        )

    async def test_unknown_workspace(self, patch_repo: PatchRepo) -> None:
        """Test that an unknown workspace is a 400.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            get_workspace_by_workspace_name=AsyncMock(
                side_effect=WorkspaceNotFoundError()
            )
        )
        with pytest.raises(BadRequestError):
            await self.call()

    async def test_caller_not_admin(self, patch_repo: PatchRepo) -> None:
        """Test that only admins of the workspace may remove users.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            get_workspace_by_workspace_name=make_workspace_db(),
            user_has_required_role_in_workspace=False,
        )
        with pytest.raises(ForbiddenError):
            await self.call()

    @pytest.mark.xfail(
        strict=True,
        raises=UserNotFoundError,
        reason="App bug: `get_user_by_id` raises `UserNotFoundError` instead of "
        "returning None, so the service's 404 branch is unreachable and the "
        "repository error escapes (HTTP 500).",
    )
    async def test_unknown_user(self, patch_repo: PatchRepo) -> None:
        """Test that an unknown user ID should be a 404.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            get_user_by_id=AsyncMock(side_effect=UserNotFoundError()),
            get_workspace_by_workspace_name=make_workspace_db(),
            user_has_required_role_in_workspace=True,
        )
        with pytest.raises(NotFoundError):
            await self.call()

    @pytest.mark.parametrize(
        "admin_ids, expected",
        [([2], ForbiddenError), ([1, 2], None), ([1], None)],
    )
    async def test_last_admin_rule(
        self,
        admin_ids: list[int],
        expected: type[Exception] | None,
        patch_repo: PatchRepo,
    ) -> None:
        """Test that the last admin of a workspace cannot be removed.

        Parameters
        ----------
        admin_ids
            IDs of the workspace's admins.
        expected
            The domain error expected, or `None` for success.
        patch_repo
            Fixture that patches service dependencies.
        """

        user_db = make_user_db(2, "target")
        workspace_db = make_workspace_db()
        patch_repo(
            get_admin_users_in_workspace=[make_user_db(i) for i in admin_ids],
            get_user_by_id=user_db,
            get_workspace_by_workspace_name=workspace_db,
            user_has_required_role_in_workspace=True,
        )
        if expected is None:
            assert await self.call() == (workspace_db, user_db)
        else:
            with pytest.raises(expected):
                await self.call()


class TestCheckCreateOrAddUserCall:
    """Tests for `check_create_or_add_user_call`."""

    async def test_unknown_workspace(self, patch_repo: PatchRepo) -> None:
        """Test that a named workspace must exist.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(
            get_workspace_by_workspace_name=AsyncMock(
                side_effect=WorkspaceNotFoundError()
            )
        )
        with pytest.raises(BadRequestError):
            await service.check_create_or_add_user_call(
                asession=AsyncMock(),
                calling_user_db=make_user_db(),
                user=UserCreate(username="new", workspace_name="missing"),
            )

    async def test_caller_not_admin_anywhere(self, patch_repo: PatchRepo) -> None:
        """Test that only admins may create users.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        patch_repo(user_has_admin_role_in_any_workspace=False)
        with pytest.raises(ForbiddenError):
            await service.check_create_or_add_user_call(
                asession=AsyncMock(),
                calling_user_db=make_user_db(),
                user=UserCreate(username="new"),
            )

    async def test_workspace_required_for_multi_workspace_admin(
        self, patch_repo: PatchRepo
    ) -> None:
        """Test that a workspace must be named when the caller administers several.

        Parameters
        ----------
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
        with pytest.raises(BadRequestError):
            await service.check_create_or_add_user_call(
                asession=AsyncMock(),
                calling_user_db=make_user_db(),
                user=UserCreate(username="new"),
            )

    @pytest.mark.parametrize(
        "workspace_has_users, expected", [(True, ForbiddenError), (False, None)]
    )
    async def test_caller_not_admin_in_named_workspace(
        self,
        expected: type[Exception] | None,
        patch_repo: PatchRepo,
        workspace_has_users: bool,
    ) -> None:
        """Test that a non-admin may only add users to a workspace with no users.

        Parameters
        ----------
        expected
            The domain error expected, or `None` for success.
        patch_repo
            Fixture that patches service dependencies.
        workspace_has_users
            Whether the named workspace already has users.
        """

        target_db = make_workspace_db(2, "target")
        patch_repo(
            get_workspace_by_workspace_name=target_db,
            get_workspaces_by_user_role=[make_workspace_db(1, "mine")],
            user_has_admin_role_in_any_workspace=True,
            users_exist_in_workspace=workspace_has_users,
        )
        user = UserCreate(username="new", workspace_name="target")
        call = service.check_create_or_add_user_call(
            asession=AsyncMock(), calling_user_db=make_user_db(), user=user
        )
        if expected is None:
            assert await call == (user, target_db)
        else:
            with pytest.raises(expected):
                await call

    async def test_defaults_filled_in(self, patch_repo: PatchRepo) -> None:
        """Test that the caller's only admin workspace and READ_ONLY role are used
        when the request omits them.

        Parameters
        ----------
        patch_repo
            Fixture that patches service dependencies.
        """

        mine_db = make_workspace_db(1, "mine")
        patch_repo(
            get_workspace_by_workspace_name=mine_db,
            get_workspaces_by_user_role=[mine_db],
            user_has_admin_role_in_any_workspace=True,
        )
        user, workspace_db = await service.check_create_or_add_user_call(
            asession=AsyncMock(),
            calling_user_db=make_user_db(),
            user=UserCreate(username="new"),
        )
        assert user.workspace_name == "mine"
        assert user.role == UserRoles.READ_ONLY
        assert workspace_db is mine_db


class TestCheckUpdateUserCall:
    """Tests for `check_update_user_call`."""

    @pytest.fixture
    def happy_path(self, patch_repo: PatchRepo) -> dict[str, AsyncMock]:
        """Patch every dependency so that the check passes.

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
            check_if_two_users_share_a_common_workspace=True,
            check_if_user_exists_in_workspace=True,
            get_user_by_id=make_user_db(2, "target"),
            get_user_role_in_workspace=UserRoles.ADMIN,
            get_workspace_by_workspace_name=make_workspace_db(),
            is_username_valid=True,
            user_has_admin_role_in_any_workspace=True,
        )

    @pytest.mark.parametrize(
        "user, override, expected",
        [
            (
                UserUpdate(username="target"),
                {"user_has_admin_role_in_any_workspace": False},
                ForbiddenError,
            ),
            (
                UserUpdate(username="target"),
                {"check_if_two_users_share_a_common_workspace": False},
                ForbiddenError,
            ),
            (UserUpdate(role=UserRoles.ADMIN, username="target"), {}, BadRequestError),
            (UserUpdate(is_default_workspace=False, username="t"), {}, BadRequestError),
            (
                UserUpdate(username="target"),
                {"get_user_by_id": AsyncMock(side_effect=UserNotFoundError())},
                NotFoundError,
            ),
            (
                UserUpdate(username="taken"),
                {"is_username_valid": False},
                BadRequestError,
            ),
            (
                UserUpdate(username="target", workspace_name="ws"),
                {"get_user_role_in_workspace": UserRoles.READ_ONLY},
                ForbiddenError,
            ),
            (
                UserUpdate(username="target", workspace_name="ws"),
                {"check_if_user_exists_in_workspace": False},
                BadRequestError,
            ),
        ],
        ids=[
            "caller-not-admin",
            "no-shared-workspace",
            "role-without-workspace",
            "default-without-workspace",
            "unknown-user",
            "username-taken",
            "caller-not-admin-in-workspace",
            "user-not-in-workspace",
        ],
    )
    async def test_errors(
        self,
        expected: type[Exception],
        happy_path: dict[str, AsyncMock],
        override: dict[str, Any],
        patch_repo: PatchRepo,
        user: UserUpdate,
    ) -> None:
        """Test each rejection branch.

        Parameters
        ----------
        expected
            The domain error the service should raise.
        happy_path
            Mocks that make the check pass (overridden per case).
        override
            Dependencies to change for this case.
        patch_repo
            Fixture that patches service dependencies.
        user
            The update payload.
        """

        patch_repo(**override)
        with pytest.raises(expected):
            await service.check_update_user_call(
                asession=AsyncMock(),
                calling_user_db=make_user_db(),
                user=user,
                user_id=2,
            )

    @pytest.mark.parametrize("workspace_name", [None, "ws"])
    async def test_allowed(
        self, happy_path: dict[str, AsyncMock], workspace_name: str | None
    ) -> None:
        """Test a valid update with and without a workspace.

        Parameters
        ----------
        happy_path
            Mocks that make the check pass.
        workspace_name
            The workspace named in the update, if any.
        """

        user_db, workspace_db = await service.check_update_user_call(
            asession=AsyncMock(),
            calling_user_db=make_user_db(),
            user=UserUpdate(username="target", workspace_name=workspace_name),
            user_id=2,
        )
        assert user_db.username == "target"
        assert (workspace_db is None) is (workspace_name is None)
