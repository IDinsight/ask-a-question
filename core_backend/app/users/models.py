"""This module contains the ORM for managing users and workspaces."""

from datetime import datetime, timezone
from typing import Sequence

import sqlalchemy.sql.functions as func
from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Row,
    String,
    case,
    exists,
    select,
    text,
    update,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..models import Base
from ..utils import get_password_salted_hash, get_random_string
from .schemas import (
    UserCreate,
    UserCreateWithCode,
    UserCreateWithPassword,
    UserResetPassword,
    UserRoles,
)
from .utils import generate_recovery_codes

PASSWORD_LENGTH = 12


class UserAlreadyExistsError(Exception):
    """Exception raised when a user already exists in the database."""


class UserNotFoundError(Exception):
    """Exception raised when a user is not found in the database."""


class UserNotFoundInWorkspaceError(Exception):
    """Exception raised when a user is not found in a workspace in the database."""


class UserWorkspaceRoleAlreadyExistsError(Exception):
    """Exception raised when a user workspace role already exists in the database."""


class UserDB(Base):
    """ORM for managing users.

    A user can belong to one or more workspaces with different roles in each workspace.
    Users do not have assigned quotas or API keys; rather, a user's API keys and quotas
    are tied to those of the workspaces they belong to. Furthermore, a user must be
    unique across all workspaces.
    """

    __tablename__ = "user"

    created_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(96), nullable=False)
    recovery_codes: Mapped[list] = mapped_column(ARRAY(String), nullable=True)
    updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    user_workspaces: Mapped[list["UserWorkspaceDB"]] = relationship(
        "UserWorkspaceDB",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    workspaces: Mapped[list["WorkspaceDB"]] = relationship(
        "WorkspaceDB", back_populates="users", secondary="user_workspace", viewonly=True
    )

    def __repr__(self) -> str:
        """Define the string representation for the `UserDB` class.

        Returns
        -------
        str
            A string representation of the `UserDB` class.
        """

        return f"<Username '{self.username}' mapped to user ID {self.user_id}>"


class WorkspaceDB(Base):
    """ORM for managing workspaces.

    A workspace is an isolated virtual environment that contains contents that can be
    accessed and modified by users assigned to that workspace. Workspaces must be
    unique but can contain duplicated content. Users can be assigned to one more
    workspaces, with different roles. In other words, there is a MANY-to-MANY
    relationship between users and workspaces.
    """

    __tablename__ = "workspace"

    api_daily_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    api_key_first_characters: Mapped[str] = mapped_column(String(5), nullable=True)
    api_key_updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    content_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    hashed_api_key: Mapped[str] = mapped_column(String(96), nullable=True, unique=True)
    updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    user_workspaces: Mapped[list["UserWorkspaceDB"]] = relationship(
        "UserWorkspaceDB",
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    users: Mapped[list["UserDB"]] = relationship(
        "UserDB", back_populates="workspaces", secondary="user_workspace", viewonly=True
    )
    workspace_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    workspace_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    def __repr__(self) -> str:
        """Define the string representation for the `WorkspaceDB` class.

        Returns
        -------
        str
            A string representation of the `WorkspaceDB` class.
        """

        return f"<Workspace '{self.workspace_name}' mapped to workspace ID `{self.workspace_id}` with API daily quota {self.api_daily_quota} and content quota {self.content_quota}>"  # noqa: E501


class UserWorkspaceDB(Base):
    """ORM for managing user in workspaces."""

    __tablename__ = "user_workspace"

    created_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    default_workspace: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),  # Ensures existing rows default to false
    )
    updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    user: Mapped["UserDB"] = relationship("UserDB", back_populates="user_workspaces")
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True
    )
    user_role: Mapped[UserRoles] = mapped_column(
        Enum(UserRoles, native_enum=False), nullable=False
    )
    workspace: Mapped["WorkspaceDB"] = relationship(
        "WorkspaceDB", back_populates="user_workspaces"
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        primary_key=True,
    )

    def __repr__(self) -> str:
        """Define the string representation for the `UserWorkspaceDB` class.

        Returns
        -------
        str
            A string representation of the `UserWorkspaceDB` class.
        """

        return f"<User ID '{self.user_id} has role '{self.user_role.value}' set for workspace ID '{self.workspace_id}'>."  # noqa: E501


async def add_existing_user_to_workspace(
    *,
    asession: AsyncSession,
    user: UserCreate,
    workspace_db: WorkspaceDB,
) -> UserCreateWithCode:
    """The process for adding an existing user to a workspace is:

    1. Retrieve the existing user from the `UserDB` database.
    2. If the default workspace is being changed for the user, then ensure that the
        old default workspace is set to `False` before the change.
    3. Add the existing user to the workspace with the specified role.

    NB: If this function is invoked, then the assumption is that it is called by an
    ADMIN user with access to the specified workspace and that this ADMIN user is
    adding an **existing** user to the workspace with the specified user role. An
    exception is made if an existing user is creating a **new** workspace---in this
    case, the existing user (admin or otherwise) is automatically added as an ADMIN
    user to the new workspace.

    NB: We do not update the API limits for the workspace when an existing user is
    added to the workspace. This is because the API limits are set at the workspace
    level when the workspace is first created by the admin and not at the user level.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user
        The user object to use for adding the existing user to the workspace.
    workspace_db
        The workspace object to use.

    Returns
    -------
    UserCreateWithCode
        The user object with the recovery codes.
    """

    assert user.role is not None
    user.is_default_workspace = user.is_default_workspace or False

    # 1.
    user_db = await get_user_by_username(asession=asession, username=user.username)

    # 2.
    if user.is_default_workspace:
        await update_user_default_workspace(
            asession=asession, user_db=user_db, workspace_db=workspace_db
        )

    # 3.
    _ = await create_user_workspace_role(
        asession=asession,
        is_default_workspace=user.is_default_workspace,
        user_db=user_db,
        user_role=user.role,
        workspace_db=workspace_db,
    )

    return UserCreateWithCode(
        is_default_workspace=user.is_default_workspace,
        recovery_codes=user_db.recovery_codes if user_db.recovery_codes else [],
        role=user.role,
        username=user_db.username,
        workspace_name=workspace_db.workspace_name,
    )


async def add_new_user_to_workspace(
    *,
    asession: AsyncSession,
    user: UserCreateWithPassword,
    workspace_db: WorkspaceDB,
) -> UserCreateWithCode:
    """The process for adding a new user to a workspace is:

    1. Generate recovery codes for the new user.
    2. Save the new user to the `UserDB` database along with their recovery codes.
    3. Add the new user to the workspace with the specified role. For new users, this
        workspace is set as their default workspace.

    NB: If this function is invoked, then the assumption is that it is called by an
    ADMIN user with access to the specified workspace and that this ADMIN user is
    adding a **new** user to the workspace with the specified user role.

    NB: We do not update the API limits for the workspace when a new user is added to
    the workspace. This is because the API limits are set at the workspace level when
    the workspace is first created by the workspace admin and not at the user level.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user
        The user object to use for adding the new user to the workspace.
    workspace_db
        The workspace object to use.

    Returns
    -------
    UserCreateWithCode
        The user object with the recovery codes.
    """

    assert user.role is not None and user.role in UserRoles

    # 1.
    recovery_codes = generate_recovery_codes()

    # 2.
    user_db = await save_user_to_db(
        asession=asession, recovery_codes=recovery_codes, user=user
    )

    # 3.
    is_default_workspace = True  # Should always be True for new users!
    _ = await create_user_workspace_role(
        asession=asession,
        is_default_workspace=is_default_workspace,
        user_db=user_db,
        user_role=user.role,
        workspace_db=workspace_db,
    )

    return UserCreateWithCode(
        is_default_workspace=is_default_workspace,
        recovery_codes=recovery_codes,
        role=user.role,
        username=user_db.username,
        workspace_name=workspace_db.workspace_name,
    )


async def check_if_two_users_share_a_common_workspace(
    *, asession: AsyncSession, user_id_1: int, user_id_2: int
) -> bool:
    """Check if two users share a common workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_id_1
        The first user ID to check.
    user_id_2
        The second user ID to check.

    Returns
    -------
    bool
        Specifies whether the two users share a common workspace.
    """

    # Subquery: select all workspace IDs belonging to user ID 2.
    user2_workspace_ids = select(UserWorkspaceDB.workspace_id).where(
        UserWorkspaceDB.user_id == user_id_2
    )

    # Main query: count how many of user1's workspace IDs intersect user2's.
    result = await asession.execute(
        select(func.count())
        .select_from(UserWorkspaceDB)
        .where(
            UserWorkspaceDB.user_id == user_id_1,
            UserWorkspaceDB.workspace_id.in_(user2_workspace_ids),
        )
    )

    shared_count = result.scalar_one()
    return shared_count > 0


async def check_if_user_exists(
    *,
    asession: AsyncSession,
    user: UserCreate | UserCreateWithPassword | UserResetPassword,
) -> UserDB | None:
    """Check if a user exists in the `UserDB` database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user
        The user object to check in the database.

    Returns
    -------
    UserDB | None
        The user object if it exists in the database, otherwise `None`.
    """

    stmt = select(UserDB).where(UserDB.username == user.username)
    result = await asession.execute(stmt)
    user_db = result.scalar_one_or_none()
    return user_db


async def check_if_user_exists_in_workspace(
    *, asession: AsyncSession, user_id: int, workspace_id: int
) -> bool:
    """Check if a user exists in the specified workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_id
        The user ID to check.
    workspace_id
        The workspace ID to check.

    Returns
    -------
    bool
        Specifies whether the user exists in the workspace.
    """

    stmt = select(
        exists().where(
            UserWorkspaceDB.user_id == user_id,
            UserWorkspaceDB.workspace_id == workspace_id,
        )
    )
    result = await asession.execute(stmt)

    return bool(result.scalar())


async def check_if_users_exist(*, asession: AsyncSession) -> bool:
    """Check if users exist in the `UserDB` database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    bool
        Specifies whether users exists in the `UserDB` database.
    """

    stmt = select(UserDB.user_id).limit(1)
    result = await asession.scalars(stmt)
    return result.first() is not None


async def check_if_user_has_default_workspace(
    *, asession: AsyncSession, user_db: UserDB
) -> bool | None:
    """Check if a user has an assigned default workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_db
        The user object to check.

    Returns
    -------
    bool | None
        Specifies whether the user has a default workspace assigned.
    """

    stmt = select(
        exists().where(
            UserWorkspaceDB.user_id == user_db.user_id,
            UserWorkspaceDB.default_workspace.is_(True),
        )
    )
    result = await asession.execute(stmt)
    return result.scalar()


async def create_user_workspace_role(
    *,
    asession: AsyncSession,
    is_default_workspace: bool = False,
    user_db: UserDB,
    user_role: UserRoles,
    workspace_db: WorkspaceDB,
) -> UserWorkspaceDB:
    """Create a user in a workspace with the specified role.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    is_default_workspace
        Specifies whether to set the workspace as the default workspace for the user.
    user_db
        The user object assigned to the workspace object.
    user_role
        The role of the user in the workspace.
    workspace_db
        The workspace object that the user object is assigned to.

    Returns
    -------
    UserWorkspaceDB
        The user workspace object saved in the database.

    Raises
    ------
    UserWorkspaceRoleAlreadyExistsError
        If the user role in the workspace already exists.
    """

    existing_user_role = await get_user_role_in_workspace(
        asession=asession, user_db=user_db, workspace_db=workspace_db
    )

    if existing_user_role is not None:
        raise UserWorkspaceRoleAlreadyExistsError(
            f"User '{user_db.username}' with role '{user_role}' in workspace "
            f"{workspace_db.workspace_name} already exists."
        )

    user_workspace_role_db = UserWorkspaceDB(
        created_datetime_utc=datetime.now(timezone.utc),
        default_workspace=is_default_workspace,
        updated_datetime_utc=datetime.now(timezone.utc),
        user_id=user_db.user_id,
        user_role=user_role,
        workspace_id=workspace_db.workspace_id,
    )

    asession.add(user_workspace_role_db)
    await asession.commit()
    await asession.refresh(user_workspace_role_db)

    return user_workspace_role_db


async def get_admin_users_in_workspace(
    *, asession: AsyncSession, workspace_id: int
) -> Sequence[UserDB] | None:
    """Retrieve all admin users for a given workspace ID.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_id
        The ID of the workspace to retrieve admin users for.

    Returns
    -------
    Sequence[UserDB] | None
        A sequence of UserDB objects representing the admin users in the workspace.
        Returns `None` if no admin users exist for that workspace.
    """

    stmt = (
        select(UserDB)
        .join(UserWorkspaceDB, UserDB.user_id == UserWorkspaceDB.user_id)
        .filter(
            UserWorkspaceDB.workspace_id == workspace_id,
            UserWorkspaceDB.user_role == UserRoles.ADMIN,
        )
    )
    result = await asession.scalars(stmt)
    admin_users = result.all()
    return admin_users if admin_users else None


async def get_user_by_id(*, asession: AsyncSession, user_id: int) -> UserDB:
    """Retrieve a user by user ID.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_id
        The user ID to use for the query.

    Returns
    -------
    UserDB
        The user object retrieved from the database.

    Raises
    ------
    UserNotFoundError
        If the user with the specified user ID does not exist.
    """

    stmt = select(UserDB).where(UserDB.user_id == user_id)
    result = await asession.execute(stmt)
    try:
        user = result.scalar_one()
        return user
    except NoResultFound as err:
        raise UserNotFoundError(f"User with user_id {user_id} does not exist.") from err


async def get_user_by_username(*, asession: AsyncSession, username: str) -> UserDB:
    """Retrieve a user by username.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    username
        The username to use for the query.

    Returns
    -------
    UserDB
        The user object retrieved from the database.

    Raises
    ------
    UserNotFoundError
        If the user with the specified username does not exist.
    """

    stmt = select(UserDB).where(UserDB.username == username)
    result = await asession.execute(stmt)
    try:
        user_db = result.scalar_one()
        return user_db
    except NoResultFound as err:
        raise UserNotFoundError(
            f"User with username {username} does not exist."
        ) from err


async def get_user_default_workspace(
    *, asession: AsyncSession, user_db: UserDB
) -> WorkspaceDB:
    """Retrieve the default workspace for a given user.

    NB: A user will have a default workspace assigned when they are created.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_db
        The user object to retrieve the default workspace for.

    Returns
    -------
    WorkspaceDB
        The default workspace object for the user.
    """

    stmt = (
        select(WorkspaceDB)
        .join(UserWorkspaceDB, UserWorkspaceDB.workspace_id == WorkspaceDB.workspace_id)
        .where(
            UserWorkspaceDB.user_id == user_db.user_id,
            UserWorkspaceDB.default_workspace.is_(True),
        )
        .limit(1)
    )

    result = await asession.execute(stmt)
    default_workspace_db = result.scalar_one()
    return default_workspace_db


async def get_user_role_in_all_workspaces(
    *, asession: AsyncSession, user_db: UserDB
) -> Sequence[Row[tuple[int, str, bool, UserRoles]]]:
    """Retrieve the workspaces a user belongs to and their roles in those workspaces.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_db
        The user object to check.

    Returns
    -------
    Sequence[Row[tuple[int, str, bool, UserRoles]]]
        A sequence of tuples containing the workspace ID, workspace name, the default
        workspace assignment, and the user role in that workspace.
    """

    stmt = (
        select(
            WorkspaceDB.workspace_id,
            WorkspaceDB.workspace_name,
            UserWorkspaceDB.default_workspace,
            UserWorkspaceDB.user_role,
        )
        .join(UserWorkspaceDB, WorkspaceDB.workspace_id == UserWorkspaceDB.workspace_id)
        .where(UserWorkspaceDB.user_id == user_db.user_id)
    )

    result = await asession.execute(stmt)
    user_roles = result.all()
    return user_roles


async def get_user_role_in_workspace(
    *, asession: AsyncSession, user_db: UserDB, workspace_db: WorkspaceDB
) -> UserRoles | None:
    """Retrieve the workspace a user belongs to and their role in the workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_db
        The user object to check.
    workspace_db
        The workspace object to check.

    Returns
    -------
    UserRoles | None
        The user role of the user in the workspace. Returns `None` if the user does not
        exist in the workspace.
    """

    stmt = select(UserWorkspaceDB.user_role).where(
        UserWorkspaceDB.user_id == user_db.user_id,
        UserWorkspaceDB.workspace_id == workspace_db.workspace_id,
    )
    result = await asession.execute(stmt)
    user_role = result.scalar_one_or_none()
    return user_role


async def get_user_workspaces(
    *, asession: AsyncSession, user_db: UserDB
) -> Sequence[WorkspaceDB]:
    """Retrieve all workspaces a user belongs to.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_db
        The user object to retrieve workspaces for.

    Returns
    -------
    Sequence[WorkspaceDB]
        A sequence of WorkspaceDB objects the user belongs to.
    """

    stmt = (
        select(WorkspaceDB)
        .join(UserWorkspaceDB, UserWorkspaceDB.workspace_id == WorkspaceDB.workspace_id)
        .where(UserWorkspaceDB.user_id == user_db.user_id)
    )
    result = await asession.execute(stmt)
    return result.scalars().all()


async def get_users_and_roles_by_workspace_id(
    *, asession: AsyncSession, workspace_id: int
) -> Sequence[Row[tuple[datetime, datetime, str, int, bool, UserRoles]]]:
    """Retrieve all users and their roles for a given workspace name.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_id
        The ID of the workspace to retrieve users and their roles for.

    Returns
    -------
    Sequence[Row[tuple[datetime, datetime, str, int, bool, UserRoles]]]
        A sequence of tuples containing the created datetime, updated datetime,
        username, user ID, default user workspace assignment, and user role for each
        user in the workspace.
    """

    stmt = (
        select(
            UserDB.created_datetime_utc,
            UserDB.updated_datetime_utc,
            UserDB.username,
            UserDB.user_id,
            UserWorkspaceDB.default_workspace,
            UserWorkspaceDB.user_role,
        )
        .join(UserWorkspaceDB, UserDB.user_id == UserWorkspaceDB.user_id)
        .join(WorkspaceDB, WorkspaceDB.workspace_id == UserWorkspaceDB.workspace_id)
        .where(WorkspaceDB.workspace_id == workspace_id)
    )

    result = await asession.execute(stmt)
    return result.all()


async def get_workspaces_by_user_role(
    *, asession: AsyncSession, user_db: UserDB, user_role: UserRoles
) -> Sequence[WorkspaceDB]:
    """Retrieve all workspaces for the user with the specified role.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_db
        The user object to get workspaces for.
    user_role
        The role of the user in the workspace.

    Returns
    -------
    Sequence[WorkspaceDB]
        A sequence of workspace objects that the user belongs to with the specified
        role.
    """

    stmt = (
        select(WorkspaceDB)
        .join(UserWorkspaceDB, WorkspaceDB.workspace_id == UserWorkspaceDB.workspace_id)
        .where(UserWorkspaceDB.user_id == user_db.user_id)
        .where(UserWorkspaceDB.user_role == user_role)
    )
    result = await asession.execute(stmt)
    return result.scalars().all()


async def is_username_valid(*, asession: AsyncSession, username: str) -> bool:
    """Check if a username is valid. A username is valid if it doesn't already exist in
    the database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    username
        The username to check.

    Returns
    -------
    bool
        Specifies if the username is valid.
    """

    stmt = select(UserDB).where(UserDB.username == username)
    result = await asession.execute(stmt)
    try:
        result.one()
        return False
    except NoResultFound:
        return True


async def remove_user_from_dbs(
    *, asession: AsyncSession, remove_from_workspace_db: WorkspaceDB, user_db: UserDB
) -> tuple[str | None, str]:
    """Remove a user from a specified workspace. If the workspace was the user's
    default workspace, then reassign the default to another assigned workspace (if
    available). If the user ends up with no workspaces at all, remove them from the
    `UserDB` database as well.

    NB: If a workspace has no users after this function completes, it is NOT deleted.
    This is because a workspace also contains contents, feedback, etc. and it is not
    clear how these artifacts should be handled at the moment.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    remove_from_workspace_db
        The workspace object to remove the user from.
    user_db
        The user object to remove from the workspace.

    Returns
    -------
    tuple[str | None, str]
        A tuple containing the user's default workspace name and the workspace from
        which the user was removed from.

    Raises
    ------
    UserNotFoundInWorkspaceError
        If the user is not found in the workspace to be removed from.
    """

    # Find the user-workspace association.
    result = await asession.execute(
        select(UserWorkspaceDB).where(
            UserWorkspaceDB.user_id == user_db.user_id,
            UserWorkspaceDB.workspace_id == remove_from_workspace_db.workspace_id,
        )
    )
    user_workspace = result.scalar_one_or_none()

    if user_workspace is None:
        raise UserNotFoundInWorkspaceError(
            f"User with ID '{user_db.user_id}' not found in workspace "
            f"'{remove_from_workspace_db.workspace_name}'."
        )

    # Remember if this workspace was set as the user's default workspace before removal.
    was_default = user_workspace.default_workspace

    # Remove the user from the specified workspace.
    await asession.delete(user_workspace)
    await asession.flush()

    # Check how many other workspaces the user is still assigned to.
    remaining_user_workspace_dbs = await get_user_workspaces(
        asession=asession, user_db=user_db
    )
    if len(remaining_user_workspace_dbs) == 0:
        # The user has no more workspaces, so remove from `UserDB` entirely.
        await asession.delete(user_db)
        await asession.commit()

        # Return `None` to indicate no default workspace remains.
        return None, remove_from_workspace_db.workspace_name

    # If the removed workspace was the default workspace, then promote the next
    # earliest workspace to the default workspace using the created datetime.
    if was_default:
        next_user_workspace_result = await asession.execute(
            select(UserWorkspaceDB)
            .where(UserWorkspaceDB.user_id == user_db.user_id)
            .order_by(UserWorkspaceDB.created_datetime_utc.asc())
            .limit(1)
        )
        next_user_workspace = next_user_workspace_result.scalar_one_or_none()
        assert next_user_workspace is not None
        next_user_workspace.default_workspace = True

        # Persist the new default workspace.
        await asession.flush()

    await asession.commit()

    # Retrieve the current default workspace name after all changes.
    default_workspace = await get_user_default_workspace(
        asession=asession, user_db=user_db
    )

    return default_workspace.workspace_name, remove_from_workspace_db.workspace_name


async def reset_user_password_in_db(
    *,
    asession: AsyncSession,
    recovery_codes: list[str] | None = None,
    user: UserResetPassword,
    user_id: int,
) -> UserDB:
    """Reset user password in the `UserDB` database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    recovery_codes
        The recovery codes for the user account recovery.
    user
        The user object to reset the password.
    user_id
        The user ID to use for the query.

    Returns
    -------
    UserDB
        The user object saved in the database after password reset.
    """

    hashed_password = get_password_salted_hash(key=user.password)
    user_db = UserDB(
        hashed_password=hashed_password,
        recovery_codes=recovery_codes,
        updated_datetime_utc=datetime.now(timezone.utc),
        user_id=user_id,
    )
    user_db = await asession.merge(user_db)
    await asession.commit()
    await asession.refresh(user_db)

    return user_db


async def save_user_to_db(
    *,
    asession: AsyncSession,
    recovery_codes: list[str] | None = None,
    user: UserCreate | UserCreateWithPassword,
) -> UserDB:
    """Save a user in the `UserDB` database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    recovery_codes
        The recovery codes for the user account recovery.
    user
        The user object to save in the database.

    Returns
    -------
    UserDB
        The user object saved in the database.

    Raises
    ------
    UserAlreadyExistsError
        If a user with the same username already exists in the database.
    """

    existing_user = await check_if_user_exists(asession=asession, user=user)

    if existing_user is not None:
        raise UserAlreadyExistsError(
            f"User with username {user.username} already exists."
        )

    if isinstance(user, UserCreateWithPassword):
        hashed_password = get_password_salted_hash(key=user.password)
    else:
        random_password = get_random_string(size=PASSWORD_LENGTH)
        hashed_password = get_password_salted_hash(key=random_password)

    user_db = UserDB(
        created_datetime_utc=datetime.now(timezone.utc),
        hashed_password=hashed_password,
        recovery_codes=recovery_codes,
        updated_datetime_utc=datetime.now(timezone.utc),
        username=user.username,
    )
    asession.add(user_db)
    await asession.commit()
    await asession.refresh(user_db)

    return user_db


async def update_user_default_workspace(
    *, asession: AsyncSession, user_db: UserDB, workspace_db: WorkspaceDB
) -> None:
    """Update the default workspace for the user to the specified workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_db
        The user object to update the default workspace for.
    workspace_db
        The workspace object to set as the default workspace.
    """

    stmt = (
        update(UserWorkspaceDB)
        .where(UserWorkspaceDB.user_id == user_db.user_id)
        .values(
            default_workspace=case(
                (UserWorkspaceDB.workspace_id == workspace_db.workspace_id, True),
                else_=False,
            )
        )
    )

    await asession.execute(stmt)
    await asession.commit()


async def update_user_in_db(
    *, asession: AsyncSession, user: UserCreate, user_id: int
) -> UserDB:
    """Update a user in the `UserDB` database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user
        The user object to update in the database.
    user_id
        The user ID to use for the query.

    Returns
    -------
    UserDB
        The user object saved in the database after update.
    """

    user_db = UserDB(
        updated_datetime_utc=datetime.now(timezone.utc),
        user_id=user_id,
        username=user.username,
    )
    user_db = await asession.merge(user_db)

    await asession.commit()
    await asession.refresh(user_db)

    return user_db


async def update_user_role_in_workspace(
    *,
    asession: AsyncSession,
    new_role: UserRoles,
    user_db: UserDB,
    workspace_db: WorkspaceDB,
) -> None:
    """Update a user's role in a given workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    new_role
        The new role to assign to the user in the workspace.
    user_db
        The user object to update the role for.
    workspace_db
        The workspace object to update the role for.

    Raises
    ------
    UserNotFoundInWorkspaceError
        If the user is not found in the workspace.
    """

    result = await asession.execute(
        update(UserWorkspaceDB)
        .where(
            UserWorkspaceDB.user_id == user_db.user_id,
            UserWorkspaceDB.workspace_id == workspace_db.workspace_id,
        )
        .values(user_role=new_role)
        .returning(UserWorkspaceDB)
    )
    updated_role_db = result.scalars().first()
    if updated_role_db is None:
        # No row updated => user not found in workspace.
        raise UserNotFoundInWorkspaceError(
            f"User with ID '{user_db.user_id}' is not found in "
            f"workspace with ID '{workspace_db.workspace_id}'."
        )

    await asession.commit()


async def users_exist_in_workspace(
    *, asession: AsyncSession, workspace_name: str
) -> bool:
    """Check if any users exist in the specified workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_name
        The name of the workspace to check for users.

    Returns
    -------
    bool
        Specifies if any users exist in the specified workspace.
    """

    stmt = (
        select(UserWorkspaceDB.user_id)
        .join(WorkspaceDB, WorkspaceDB.workspace_id == UserWorkspaceDB.workspace_id)
        .where(WorkspaceDB.workspace_name == workspace_name)
        .limit(1)
    )
    result = await asession.scalar(stmt)
    return result is not None


async def user_has_admin_role_in_any_workspace(
    *, asession: AsyncSession, user_db: UserDB
) -> bool:
    """Check if a user has the ADMIN role in any workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_db
        The user object to check.

    Returns
    -------
    bool
        Specifies if the user has an ADMIN role in at least one workspace.
    """

    stmt = (
        select(UserWorkspaceDB.user_id)
        .where(
            UserWorkspaceDB.user_id == user_db.user_id,
            UserWorkspaceDB.user_role == UserRoles.ADMIN,
        )
        .limit(1)
    )
    result = await asession.execute(stmt)
    return result.scalar_one_or_none() is not None


async def user_has_required_role_in_workspace(
    *,
    allowed_user_roles: UserRoles | list[UserRoles],
    asession: AsyncSession,
    user_db: UserDB,
    workspace_db: WorkspaceDB,
) -> bool:
    """Check if the user has the required role to operate in the specified workspace.

    Parameters
    ----------
    allowed_user_roles
        The allowed user roles that can operate in the specified workspace.
    asession
        The SQLAlchemy async session to use for all database connections.
    user_db
        The user object to check the role for.
    workspace_db
        The workspace to check the user role against.
    """

    if not isinstance(allowed_user_roles, list):
        allowed_user_roles = [allowed_user_roles]
    user_role_in_specified_workspace = await get_user_role_in_workspace(
        asession=asession, user_db=user_db, workspace_db=workspace_db
    )
    return user_role_in_specified_workspace in allowed_user_roles
