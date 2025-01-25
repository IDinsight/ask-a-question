"""This module contains the ORM for managing users and workspaces."""

from datetime import datetime, timezone

from sqlalchemy import (
    ARRAY,
    DateTime,
    ForeignKey,
    Integer,
    Row,
    Sequence,
    String,
    select,
    update,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SQLAlchemyEnum

from ..models import Base
from ..utils import get_password_salted_hash, get_random_string
from .schemas import UserCreate, UserCreateWithPassword, UserResetPassword, UserRoles

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
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    workspaces: Mapped[list["WorkspaceDB"]] = relationship(
        "WorkspaceDB",
        back_populates="users",
        secondary="user_workspace_association",
        viewonly=True,
    )
    workspace_roles: Mapped[list["UserWorkspaceRoleDB"]] = relationship(
        "UserWorkspaceRoleDB", back_populates="user"
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

    api_daily_quota: Mapped[int] = mapped_column(Integer, nullable=True)
    api_key_first_characters: Mapped[str] = mapped_column(String(5), nullable=True)
    api_key_updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    content_quota: Mapped[int] = mapped_column(Integer, nullable=True)
    created_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    hashed_api_key: Mapped[str] = mapped_column(String(96), nullable=True, unique=True)
    updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    users: Mapped[list["UserDB"]] = relationship(
        "UserDB",
        back_populates="workspaces",
        secondary="user_workspace_association",
        viewonly=True,
    )
    workspace_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    workspace_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    workspace_roles: Mapped[list["UserWorkspaceRoleDB"]] = relationship(
        "UserWorkspaceRoleDB", back_populates="workspace"
    )

    def __repr__(self) -> str:
        """Define the string representation for the `WorkspaceDB` class.

        Returns
        -------
        str
            A string representation of the `WorkspaceDB` class.
        """

        return f"<Workspace '{self.workspace_name}' mapped to workspace ID `{self.workspace_id}` with API daily quota {self.api_daily_quota} and content quota {self.content_quota}>"  # noqa: E501


class UserWorkspaceRoleDB(Base):
    """ORM for managing user roles in workspaces."""

    __tablename__ = "user_workspace_association"

    created_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    user: Mapped["UserDB"] = relationship("UserDB", back_populates="workspace_roles")
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), primary_key=True
    )
    user_role: Mapped[UserRoles] = mapped_column(
        SQLAlchemyEnum(UserRoles), nullable=False
    )
    workspace: Mapped["WorkspaceDB"] = relationship(
        "WorkspaceDB", back_populates="workspace_roles"
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspace.workspace_id"), primary_key=True
    )

    def __repr__(self) -> str:
        """Define the string representation for the `UserWorkspaceRoleDB` class.

        Returns
        -------
        str
            A string representation of the `UserWorkspaceRoleDB` class.
        """

        return f"<Role '{self.user_role.value}' set for user ID '{self.user_id} in workspace ID '{self.workspace_id}'>."  # noqa: E501


async def add_user_workspace_role(
    *,
    asession: AsyncSession,
    user_db: UserDB,
    user_role: UserRoles,
    workspace_db: WorkspaceDB,
) -> UserWorkspaceRoleDB:
    """Add a user to a workspace with the specified role.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_db
        The user object assigned to the workspace object.
    user_role
        The role of the user in the workspace.
    workspace_db
        The workspace object that the user object is assigned to.

    Returns
    -------
    UserWorkspaceRoleDB
        The user workspace role object saved in the database.

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

    user_workspace_role_db = UserWorkspaceRoleDB(
        created_datetime_utc=datetime.now(timezone.utc),
        updated_datetime_utc=datetime.now(timezone.utc),
        user_id=user_db.user_id,
        user_role=user_role,
        workspace_id=workspace_db.workspace_id,
    )

    asession.add(user_workspace_role_db)
    await asession.commit()
    await asession.refresh(user_workspace_role_db)

    return user_workspace_role_db


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
    user = result.scalar_one_or_none()
    return user


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


async def get_user_role_in_all_workspaces(
    *, asession: AsyncSession, user_db: UserDB
) -> Sequence[Row[tuple[str, UserRoles]]]:
    """Retrieve the workspaces a user belongs to and their roles in those workspaces.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    user_db
        The user object to check.

    Returns
    -------
    Sequence[Row[tuple[str, UserRoles]]]
        A sequence of tuples containing the workspace name and the user role in that
        workspace.
    """

    stmt = (
        select(WorkspaceDB.workspace_name, UserWorkspaceRoleDB.user_role)
        .join(
            UserWorkspaceRoleDB,
            WorkspaceDB.workspace_id == UserWorkspaceRoleDB.workspace_id,
        )
        .where(UserWorkspaceRoleDB.user_id == user_db.user_id)
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

    stmt = select(UserWorkspaceRoleDB.user_role).where(
        UserWorkspaceRoleDB.user_id == user_db.user_id,
        UserWorkspaceRoleDB.workspace_id == workspace_db.workspace_id,
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
        .join(
            UserWorkspaceRoleDB,
            UserWorkspaceRoleDB.workspace_id == WorkspaceDB.workspace_id,
        )
        .where(UserWorkspaceRoleDB.user_id == user_db.user_id)
    )
    result = await asession.execute(stmt)
    return result.scalars().all()


async def get_users_and_roles_by_workspace_name(
    *, asession: AsyncSession, workspace_name: str
) -> Sequence[Row[tuple[datetime, datetime, str, int, UserRoles]]]:
    """Retrieve all users and their roles for a given workspace name.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_name
        The name of the workspace to retrieve users and their roles for.

    Returns
    -------
    Sequence[Row[tuple[datetime, datetime, str, int, UserRoles]]]
        A sequence of tuples containing the created datetime, updated datetime,
        username, user ID, and user role for each user in the workspace.
    """

    stmt = (
        select(
            UserDB.created_datetime_utc,
            UserDB.updated_datetime_utc,
            UserDB.username,
            UserDB.user_id,
            UserWorkspaceRoleDB.user_role,
        )
        .join(UserWorkspaceRoleDB, UserDB.user_id == UserWorkspaceRoleDB.user_id)
        .join(WorkspaceDB, WorkspaceDB.workspace_id == UserWorkspaceRoleDB.workspace_id)
        .where(WorkspaceDB.workspace_name == workspace_name)
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
        .join(
            UserWorkspaceRoleDB,
            WorkspaceDB.workspace_id == UserWorkspaceRoleDB.workspace_id,
        )
        .where(UserWorkspaceRoleDB.user_id == user_db.user_id)
        .where(UserWorkspaceRoleDB.user_role == user_role)
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
    """

    stmt = select(UserDB).where(UserDB.username == username)
    result = await asession.execute(stmt)
    try:
        result.one()
        return False
    except NoResultFound:
        return True


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

    hashed_password = get_password_salted_hash(user.password)
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
        hashed_password = get_password_salted_hash(user.password)
    else:
        random_password = get_random_string(PASSWORD_LENGTH)
        hashed_password = get_password_salted_hash(random_password)

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
        update(UserWorkspaceRoleDB)
        .where(
            UserWorkspaceRoleDB.user_id == user_db.user_id,
            UserWorkspaceRoleDB.workspace_id == workspace_db.workspace_id,
        )
        .values(user_role=new_role)
        .returning(UserWorkspaceRoleDB)
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
        select(UserWorkspaceRoleDB.user_id)
        .join(WorkspaceDB, WorkspaceDB.workspace_id == UserWorkspaceRoleDB.workspace_id)
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
        select(UserWorkspaceRoleDB.user_id)
        .where(
            UserWorkspaceRoleDB.user_id == user_db.user_id,
            UserWorkspaceRoleDB.user_role == UserRoles.ADMIN,
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
