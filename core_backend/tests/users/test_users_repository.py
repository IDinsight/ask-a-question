"""Tests for `app.users.repository`.

Every test runs against the real database through `rollback_asession`, so rows are
created per test and discarded on teardown (no clean-up code needed).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password_salted_hash
from app.users.repository import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UserNotFoundInWorkspaceError,
    UserWorkspaceRoleAlreadyExistsError,
    add_existing_user_to_workspace,
    add_new_user_to_workspace,
    check_if_two_users_share_a_common_workspace,
    check_if_user_exists,
    check_if_user_exists_in_workspace,
    check_if_user_has_default_workspace,
    check_if_users_exist,
    create_user_workspace_role,
    get_admin_users_in_workspace,
    get_user_by_id,
    get_user_by_username,
    get_user_default_workspace,
    get_user_role_in_all_workspaces,
    get_user_role_in_workspace,
    get_user_workspaces,
    get_users_and_roles_by_workspace_id,
    get_workspaces_by_user_role,
    is_username_valid,
    remove_user_from_dbs,
    reset_user_password_in_db,
    save_user_to_db,
    update_user_default_workspace,
    update_user_in_db,
    update_user_role_in_workspace,
    user_has_admin_role_in_any_workspace,
    user_has_required_role_in_workspace,
    users_exist_in_workspace,
)
from app.users.schemas import (
    UserCreate,
    UserCreateWithPassword,
    UserResetPassword,
    UserRoles,
)
from tests.users.conftest import (
    AddToWorkspace,
    MakeUser,
    MakeWorkspace,
    unique_name,
)

NEW_PASSWORD = "brand_new_password"  # pragma: allowlist secret


class TestSaveAndGetUser:
    """Tests for saving users and looking them up."""

    async def test_save_user_to_db(self, rollback_asession: AsyncSession) -> None:
        """Test saving a user (without a password) to the database.

        Parameters
        ----------
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        username = unique_name("saved_user")
        user = UserCreate(
            is_default_workspace=True,
            role=UserRoles.READ_ONLY,
            username=username,
            workspace_name="any_workspace",
        )
        saved_user = await save_user_to_db(asession=rollback_asession, user=user)
        assert saved_user.username == username
        assert saved_user.user_id is not None
        # A random password is generated, so a hash is still stored.
        assert saved_user.hashed_password

    async def test_save_user_to_db_hashes_given_password(
        self, rollback_asession: AsyncSession
    ) -> None:
        """Test that the password and recovery codes passed in are stored.

        Parameters
        ----------
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user = UserCreateWithPassword(
            password=NEW_PASSWORD, username=unique_name("pw_user")
        )
        saved_user = await save_user_to_db(
            asession=rollback_asession, recovery_codes=["code"], user=user
        )
        assert verify_password_salted_hash(
            key=NEW_PASSWORD, stored_hash=saved_user.hashed_password
        )
        assert saved_user.recovery_codes == ["code"]

    async def test_save_user_to_db_existing_user(
        self, make_user: MakeUser, rollback_asession: AsyncSession
    ) -> None:
        """Test saving a user to the database when the user already exists.

        Parameters
        ----------
        make_user
            Factory that inserts a user.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user_db = await make_user()
        with pytest.raises(UserAlreadyExistsError):
            await save_user_to_db(
                asession=rollback_asession, user=UserCreate(username=user_db.username)
            )

    async def test_get_user_by_username(
        self, make_user: MakeUser, rollback_asession: AsyncSession
    ) -> None:
        """Test getting a user by their username.

        Parameters
        ----------
        make_user
            Factory that inserts a user.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user_db = await make_user()
        retrieved_user = await get_user_by_username(
            asession=rollback_asession, username=user_db.username
        )
        assert retrieved_user.user_id == user_db.user_id

    async def test_get_user_by_username_no_user(
        self, rollback_asession: AsyncSession
    ) -> None:
        """Test getting a user by their username when the user does not exist.

        Parameters
        ----------
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        with pytest.raises(UserNotFoundError):
            await get_user_by_username(
                asession=rollback_asession, username="nonexistent"
            )

    async def test_get_user_by_id(
        self, make_user: MakeUser, rollback_asession: AsyncSession
    ) -> None:
        """Test getting a user by ID, and the error raised for an unknown ID.

        Parameters
        ----------
        make_user
            Factory that inserts a user.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user_db = await make_user()
        retrieved_user = await get_user_by_id(
            asession=rollback_asession, user_id=user_db.user_id
        )
        assert retrieved_user.username == user_db.username

        with pytest.raises(UserNotFoundError):
            await get_user_by_id(asession=rollback_asession, user_id=-1)

    async def test_existence_checks(
        self, make_user: MakeUser, rollback_asession: AsyncSession
    ) -> None:
        """Test `check_if_user_exists`, `check_if_users_exist` and
        `is_username_valid`.

        Parameters
        ----------
        make_user
            Factory that inserts a user.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user_db = await make_user()

        found = await check_if_user_exists(
            asession=rollback_asession, user=UserCreate(username=user_db.username)
        )
        assert found is not None and found.user_id == user_db.user_id
        assert (
            await check_if_user_exists(
                asession=rollback_asession, user=UserCreate(username="nonexistent")
            )
            is None
        )
        assert await check_if_users_exist(asession=rollback_asession) is True
        assert (
            await is_username_valid(
                asession=rollback_asession, username=user_db.username
            )
            is False
        )
        assert (
            await is_username_valid(asession=rollback_asession, username="nonexistent")
            is True
        )


class TestAddUserToWorkspace:
    """Tests for adding new and existing users to workspaces."""

    async def test_add_new_user_to_workspace(
        self, make_workspace: MakeWorkspace, rollback_asession: AsyncSession
    ) -> None:
        """Test that a new user is saved, given recovery codes and made a member of
        the workspace, which becomes their default.

        Parameters
        ----------
        make_workspace
            Factory that inserts a workspace.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        workspace_db = await make_workspace()
        user = UserCreateWithPassword(
            password=NEW_PASSWORD,
            role=UserRoles.READ_ONLY,
            username=unique_name("new_user"),
            workspace_name=workspace_db.workspace_name,
        )

        created = await add_new_user_to_workspace(
            asession=rollback_asession, user=user, workspace_db=workspace_db
        )

        assert created.is_default_workspace is True
        assert len(created.recovery_codes) == 5
        assert created.workspace_name == workspace_db.workspace_name
        user_db = await get_user_by_username(
            asession=rollback_asession, username=user.username
        )
        assert (
            await get_user_role_in_workspace(
                asession=rollback_asession, user_db=user_db, workspace_db=workspace_db
            )
            == UserRoles.READ_ONLY
        )

    @pytest.mark.parametrize("is_default_workspace", [True, None])
    async def test_add_existing_user_to_workspace(
        self,
        add_to_workspace: AddToWorkspace,
        is_default_workspace: bool | None,
        make_user: MakeUser,
        make_workspace: MakeWorkspace,
        rollback_asession: AsyncSession,
    ) -> None:
        """Test adding an existing user to a second workspace, optionally making it
        their default.

        Parameters
        ----------
        add_to_workspace
            Factory that assigns a user to a workspace.
        is_default_workspace
            Whether the new workspace should become the user's default.
        make_user
            Factory that inserts a user.
        make_workspace
            Factory that inserts a workspace.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user_db = await make_user()
        first_workspace_db = await make_workspace()
        second_workspace_db = await make_workspace()
        await add_to_workspace(user_db, first_workspace_db, default=True)

        added = await add_existing_user_to_workspace(
            asession=rollback_asession,
            user=UserCreate(
                is_default_workspace=is_default_workspace,
                role=UserRoles.ADMIN,
                username=user_db.username,
            ),
            workspace_db=second_workspace_db,
        )

        # `None` is normalised to `False`; users without codes get an empty list.
        assert added.is_default_workspace is bool(is_default_workspace)
        assert added.recovery_codes == []
        default_workspace_db = await get_user_default_workspace(
            asession=rollback_asession, user_db=user_db
        )
        expected_default = (
            second_workspace_db if is_default_workspace else first_workspace_db
        )
        assert default_workspace_db.workspace_id == expected_default.workspace_id

    async def test_create_user_workspace_role_twice_fails(
        self,
        make_user: MakeUser,
        make_workspace: MakeWorkspace,
        rollback_asession: AsyncSession,
    ) -> None:
        """Test that a user cannot be given two roles in the same workspace.

        Parameters
        ----------
        make_user
            Factory that inserts a user.
        make_workspace
            Factory that inserts a workspace.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user_db = await make_user()
        workspace_db = await make_workspace()
        role_db = await create_user_workspace_role(
            asession=rollback_asession,
            user_db=user_db,
            user_role=UserRoles.ADMIN,
            workspace_db=workspace_db,
        )
        assert role_db.default_workspace is False

        with pytest.raises(UserWorkspaceRoleAlreadyExistsError):
            await create_user_workspace_role(
                asession=rollback_asession,
                user_db=user_db,
                user_role=UserRoles.READ_ONLY,
                workspace_db=workspace_db,
            )


class TestUserWorkspaceQueries:
    """Tests for the read-only queries about users, workspaces and roles."""

    async def test_membership_queries(
        self,
        add_to_workspace: AddToWorkspace,
        make_user: MakeUser,
        make_workspace: MakeWorkspace,
        rollback_asession: AsyncSession,
    ) -> None:
        """Test the queries that look up a user's workspaces and roles.

        Setup: `admin` is ADMIN in A (default) and READ_ONLY in B; `reader` is
        READ_ONLY in A (default); `loner` belongs to no workspace.

        Parameters
        ----------
        add_to_workspace
            Factory that assigns a user to a workspace.
        make_user
            Factory that inserts a user.
        make_workspace
            Factory that inserts a workspace.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        admin = await make_user()
        reader = await make_user()
        loner = await make_user()
        workspace_a = await make_workspace()
        workspace_b = await make_workspace()
        await add_to_workspace(admin, workspace_a, default=True)
        await add_to_workspace(admin, workspace_b, role=UserRoles.READ_ONLY)
        await add_to_workspace(
            reader, workspace_a, role=UserRoles.READ_ONLY, default=True
        )
        s = rollback_asession

        # Shared workspaces.
        assert await check_if_two_users_share_a_common_workspace(
            asession=s, user_id_1=admin.user_id, user_id_2=reader.user_id
        )
        assert not await check_if_two_users_share_a_common_workspace(
            asession=s, user_id_1=admin.user_id, user_id_2=loner.user_id
        )

        # Membership of a single workspace.
        assert await check_if_user_exists_in_workspace(
            asession=s, user_id=reader.user_id, workspace_id=workspace_a.workspace_id
        )
        assert not await check_if_user_exists_in_workspace(
            asession=s, user_id=reader.user_id, workspace_id=workspace_b.workspace_id
        )

        # Default workspace.
        assert await check_if_user_has_default_workspace(asession=s, user_db=admin)
        assert not await check_if_user_has_default_workspace(asession=s, user_db=loner)
        default_db = await get_user_default_workspace(asession=s, user_db=admin)
        assert default_db.workspace_id == workspace_a.workspace_id

        # Roles.
        assert (
            await get_user_role_in_workspace(
                asession=s, user_db=admin, workspace_db=workspace_b
            )
            == UserRoles.READ_ONLY
        )
        assert (
            await get_user_role_in_workspace(
                asession=s, user_db=loner, workspace_db=workspace_a
            )
            is None
        )
        all_roles = await get_user_role_in_all_workspaces(asession=s, user_db=admin)
        assert {(r.workspace_id, r.user_role) for r in all_roles} == {
            (workspace_a.workspace_id, UserRoles.ADMIN),
            (workspace_b.workspace_id, UserRoles.READ_ONLY),
        }

        # Workspaces of a user.
        workspaces = await get_user_workspaces(asession=s, user_db=admin)
        assert {w.workspace_id for w in workspaces} == {
            workspace_a.workspace_id,
            workspace_b.workspace_id,
        }
        admin_workspaces = await get_workspaces_by_user_role(
            asession=s, user_db=admin, user_role=UserRoles.ADMIN
        )
        assert [w.workspace_id for w in admin_workspaces] == [workspace_a.workspace_id]

        # Users of a workspace.
        rows = await get_users_and_roles_by_workspace_id(
            asession=s, workspace_id=workspace_a.workspace_id
        )
        assert {(r.username, r.user_role) for r in rows} == {
            (admin.username, UserRoles.ADMIN),
            (reader.username, UserRoles.READ_ONLY),
        }
        assert await users_exist_in_workspace(
            asession=s, workspace_name=workspace_a.workspace_name
        )
        assert not await users_exist_in_workspace(
            asession=s, workspace_name="no_such_workspace"
        )

    async def test_admin_role_queries(
        self,
        add_to_workspace: AddToWorkspace,
        make_user: MakeUser,
        make_workspace: MakeWorkspace,
        rollback_asession: AsyncSession,
    ) -> None:
        """Test the queries that check for ADMIN / required roles.

        Parameters
        ----------
        add_to_workspace
            Factory that assigns a user to a workspace.
        make_user
            Factory that inserts a user.
        make_workspace
            Factory that inserts a workspace.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        admin = await make_user()
        reader = await make_user()
        workspace_db = await make_workspace()
        empty_workspace_db = await make_workspace()
        await add_to_workspace(admin, workspace_db)
        await add_to_workspace(reader, workspace_db, role=UserRoles.READ_ONLY)
        s = rollback_asession

        admins = await get_admin_users_in_workspace(
            asession=s, workspace_id=workspace_db.workspace_id
        )
        assert admins is not None
        assert [a.user_id for a in admins] == [admin.user_id]
        assert (
            await get_admin_users_in_workspace(
                asession=s, workspace_id=empty_workspace_db.workspace_id
            )
            is None
        )

        assert await user_has_admin_role_in_any_workspace(asession=s, user_db=admin)
        assert not await user_has_admin_role_in_any_workspace(
            asession=s, user_db=reader
        )

        # A single role is accepted as well as a list of roles.
        assert await user_has_required_role_in_workspace(
            allowed_user_roles=UserRoles.ADMIN,
            asession=s,
            user_db=admin,
            workspace_db=workspace_db,
        )
        assert not await user_has_required_role_in_workspace(
            allowed_user_roles=[UserRoles.ADMIN],
            asession=s,
            user_db=reader,
            workspace_db=workspace_db,
        )


class TestUpdateUser:
    """Tests for the functions that update users and their roles."""

    async def test_reset_user_password_in_db(
        self, make_user: MakeUser, rollback_asession: AsyncSession
    ) -> None:
        """Test that the password hash and recovery codes are replaced.

        Parameters
        ----------
        make_user
            Factory that inserts a user.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user_db = await make_user(recovery_codes=["a", "b"])
        updated = await reset_user_password_in_db(
            asession=rollback_asession,
            recovery_codes=["b"],
            user=UserResetPassword(
                password=NEW_PASSWORD, recovery_code="a", username=user_db.username
            ),
            user_id=user_db.user_id,
        )
        assert updated.recovery_codes == ["b"]
        assert verify_password_salted_hash(
            key=NEW_PASSWORD, stored_hash=updated.hashed_password
        )

    async def test_update_user_in_db(
        self, make_user: MakeUser, rollback_asession: AsyncSession
    ) -> None:
        """Test renaming a user.

        Parameters
        ----------
        make_user
            Factory that inserts a user.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user_db = await make_user()
        new_username = unique_name("renamed")
        updated = await update_user_in_db(
            asession=rollback_asession,
            user=UserCreate(username=new_username),
            user_id=user_db.user_id,
        )
        assert updated.username == new_username

    async def test_update_user_default_workspace(
        self,
        add_to_workspace: AddToWorkspace,
        make_user: MakeUser,
        make_workspace: MakeWorkspace,
        rollback_asession: AsyncSession,
    ) -> None:
        """Test moving the default flag to another workspace.

        Parameters
        ----------
        add_to_workspace
            Factory that assigns a user to a workspace.
        make_user
            Factory that inserts a user.
        make_workspace
            Factory that inserts a workspace.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user_db = await make_user()
        old_default = await make_workspace()
        new_default = await make_workspace()
        await add_to_workspace(user_db, old_default, default=True)
        await add_to_workspace(user_db, new_default)

        await update_user_default_workspace(
            asession=rollback_asession, user_db=user_db, workspace_db=new_default
        )

        rows = await get_user_role_in_all_workspaces(
            asession=rollback_asession, user_db=user_db
        )
        defaults = {r.workspace_id: r.default_workspace for r in rows}
        assert defaults == {
            old_default.workspace_id: False,
            new_default.workspace_id: True,
        }

    async def test_update_user_role_in_workspace(
        self,
        add_to_workspace: AddToWorkspace,
        make_user: MakeUser,
        make_workspace: MakeWorkspace,
        rollback_asession: AsyncSession,
    ) -> None:
        """Test changing a role, and the error for a user outside the workspace.

        Parameters
        ----------
        add_to_workspace
            Factory that assigns a user to a workspace.
        make_user
            Factory that inserts a user.
        make_workspace
            Factory that inserts a workspace.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user_db = await make_user()
        workspace_db = await make_workspace()
        other_workspace_db = await make_workspace()
        await add_to_workspace(user_db, workspace_db, role=UserRoles.READ_ONLY)

        await update_user_role_in_workspace(
            asession=rollback_asession,
            new_role=UserRoles.ADMIN,
            user_db=user_db,
            workspace_db=workspace_db,
        )
        assert (
            await get_user_role_in_workspace(
                asession=rollback_asession, user_db=user_db, workspace_db=workspace_db
            )
            == UserRoles.ADMIN
        )

        with pytest.raises(UserNotFoundInWorkspaceError):
            await update_user_role_in_workspace(
                asession=rollback_asession,
                new_role=UserRoles.ADMIN,
                user_db=user_db,
                workspace_db=other_workspace_db,
            )


class TestRemoveUserFromDbs:
    """Tests for `remove_user_from_dbs`."""

    async def test_user_not_in_workspace(
        self,
        make_user: MakeUser,
        make_workspace: MakeWorkspace,
        rollback_asession: AsyncSession,
    ) -> None:
        """Test that removing a user from a workspace they are not in fails.

        Parameters
        ----------
        make_user
            Factory that inserts a user.
        make_workspace
            Factory that inserts a workspace.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user_db = await make_user()
        workspace_db = await make_workspace()
        with pytest.raises(UserNotFoundInWorkspaceError):
            await remove_user_from_dbs(
                asession=rollback_asession,
                remove_from_workspace_db=workspace_db,
                user_db=user_db,
            )

    async def test_removing_last_workspace_deletes_user(
        self,
        add_to_workspace: AddToWorkspace,
        make_user: MakeUser,
        make_workspace: MakeWorkspace,
        rollback_asession: AsyncSession,
    ) -> None:
        """Test that a user left without workspaces is deleted.

        Parameters
        ----------
        add_to_workspace
            Factory that assigns a user to a workspace.
        make_user
            Factory that inserts a user.
        make_workspace
            Factory that inserts a workspace.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user_db = await make_user()
        workspace_db = await make_workspace()
        await add_to_workspace(user_db, workspace_db, default=True)

        default_name, removed_name = await remove_user_from_dbs(
            asession=rollback_asession,
            remove_from_workspace_db=workspace_db,
            user_db=user_db,
        )

        assert default_name is None
        assert removed_name == workspace_db.workspace_name
        with pytest.raises(UserNotFoundError):
            await get_user_by_username(
                asession=rollback_asession, username=user_db.username
            )

    @pytest.mark.parametrize("remove_default", [True, False])
    async def test_removing_one_of_several_workspaces(
        self,
        add_to_workspace: AddToWorkspace,
        make_user: MakeUser,
        make_workspace: MakeWorkspace,
        remove_default: bool,
        rollback_asession: AsyncSession,
    ) -> None:
        """Test removal from one of three workspaces.

        When the default workspace is removed, the earliest remaining membership
        (by created timestamp) becomes the new default; otherwise the default is
        unchanged.

        Parameters
        ----------
        add_to_workspace
            Factory that assigns a user to a workspace.
        make_user
            Factory that inserts a user.
        make_workspace
            Factory that inserts a workspace.
        remove_default
            Whether the workspace removed is the user's default.
        rollback_asession
            Session whose writes are rolled back after the test.
        """

        user_db = await make_user()
        default_ws = await make_workspace()
        earliest_ws = await make_workspace()
        latest_ws = await make_workspace()
        await add_to_workspace(user_db, default_ws, default=True)
        # Offsets make `earliest_ws` the first candidate for promotion.
        await add_to_workspace(user_db, earliest_ws, created_offset_s=-60)
        await add_to_workspace(user_db, latest_ws, created_offset_s=60)

        remove_ws = default_ws if remove_default else latest_ws
        default_name, removed_name = await remove_user_from_dbs(
            asession=rollback_asession,
            remove_from_workspace_db=remove_ws,
            user_db=user_db,
        )

        expected_default = earliest_ws if remove_default else default_ws
        assert default_name == expected_default.workspace_name
        assert removed_name == remove_ws.workspace_name
