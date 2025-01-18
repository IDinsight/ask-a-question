"""This module contains the ORM for managing users and workspaces."""

from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import (
    ARRAY,
    DateTime,
    ForeignKey,
    Integer,
    String,
    exists,
    func,
    select,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, joinedload, mapped_column, relationship
from sqlalchemy.types import Enum as SQLAlchemyEnum

from ..models import Base
from ..utils import get_key_hash, get_password_salted_hash, get_random_string
from .schemas import UserCreate, UserCreateWithPassword, UserResetPassword, UserRoles

PASSWORD_LENGTH = 12


class UserNotFoundError(Exception):
    """Exception raised when a user is not found in the database."""


class UserAlreadyExistsError(Exception):
    """Exception raised when a user already exists in the database."""


class UserWorkspaceRoleAlreadyExistsError(Exception):
    """Exception raised when a user workspace role already exists in the database."""


class WorkspaceAlreadyExistsError(Exception):
    """Exception raised when a workspace already exists in the database."""


class UserDB(Base):
    """SQL Alchemy data model for users."""

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
    workspace_roles: Mapped[list["UserWorkspaceRoleDB"]] = relationship(
        "UserWorkspaceRoleDB", back_populates="user"
    )
    workspaces: Mapped[list["WorkspaceDB"]] = relationship(
        "WorkspaceDB",
        back_populates="users",
        secondary="user_workspace_association",
        viewonly=True,
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
    """SQL Alchemy data model for workspaces.

    A workspace is an isolated virtual environment that contains contents that can be
    accessed and modified by users assigned to that workspace. Workspaces must be
    unique but can contain duplicated content. Users can be assigned to one more
    workspaces, with different roles. In other words, there is a MANY-to-MANY
    relationship between users and workspaces.

    The following scenarios apply:

    1. Nothing Exists
        User 1 must first create an account as an ADMIN user. Then, User 1 can create
        new Workspace A and add themselves as and ADMIN user to Workspace A. User 2
        wants to join Workspace A. User 1 can add User 2 to Workspace A as an ADMIN or
        READ ONLY user. If User 2 is added as an ADMIN user, then User 2 has the same
        privileges as User 1 within Workspace A. If User 2 is added as a READ ONLY
        user, then User 2 can only read contents in Workspace A.

    2. Multiple Workspaces
        User 1 is ADMIN of Workspace A and User 3 is ADMIN of Workspace B. User 2 is a
        READ ONLY user in Workspace A. User 3 invites User 2 to be an ADMIN of
        Workspace B. User 2 is now a READ ONLY user in Workspace A and an ADMIN in
        Workspace B. User 2 can only read contents in Workspace A but can read and
        modify contents in Workspace B as well as add/delete users from Workspace B.

    3. Creating/Deleting New Workspaces
        User 1 is an ADMIN of Workspace A. Users 2 and 3 are ADMINs of Workspace B.
        User 1 can create a new workspace but cannot delete/modify Workspace B. Users
        2 and 3 can create a new workspace but delete/modify Workspace A.
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

        return f"<Workspace '{self.workspace_name}' mapped to workspace ID `{self.workspace_id}` with API daily quota {self.api_daily_quota} and content quota {self.content_quota}>"


class UserWorkspaceRoleDB(Base):
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

        return f"<Role '{self.user_role.value}' set for user ID '{self.user_id} in workspace ID '{self.workspace_id}'>."


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

    stmt = select(exists().where(UserDB.user_id != None))
    result = await asession.execute(stmt)
    return result.scalar()


async def check_if_workspace_exists(
    *, asession: AsyncSession, workspace_name: str
) -> WorkspaceDB | None:
    """Check if the specified workspace exists in the `WorkspaceDB` database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_name
        The workspace name to check.

    Returns
    -------
    WorkspaceDB | None
        The workspace object if it exists in the database. Returns `None` if the
        workspace does not exist.
    """

    stmt = select(WorkspaceDB).where(WorkspaceDB.workspace_name == workspace_name)
    result = await asession.execute(stmt)
    return result.scalar_one_or_none()


async def check_if_workspaces_exist(*, asession: AsyncSession) -> bool:
    """Check if workspaces exist in the `WorkspaceDB` database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    bool
        Specifies whether workspaces exist in the `WorkspaceDB` database.
    """

    stmt = select(exists().where(WorkspaceDB.workspace_id != None))
    result = await asession.execute(stmt)
    return result.scalar()


async def get_all_user_roles_in_workspaces(
    *, asession: AsyncSession
) -> Sequence[UserDB]:
    """Get all user roles in all workspaces.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    Sequence[UserDB]
        A sequence of user objects with their roles in the workspaces.
    """

    stmt = select(UserDB).options(joinedload(UserDB.workspace_roles).joinedload(
        UserWorkspaceRoleDB.workspace)
    )
    result = await asession.execute(stmt)
    users = result.unique().scalars().all()
    return users


async def get_or_create_workspace(
    *,
    api_daily_quota: Optional[int] = None,
    asession: AsyncSession,
    content_quota: Optional[int] = None,
    workspace_name: Optional[str] = None,
) -> WorkspaceDB:
    """Create a workspace in the `WorkspaceDB` database. If the workspace already
    exists, then it is returned.

    NB: The assumption here is that this function is invoked by an ADMIN user with
    access to the workspace.

    Parameters
    ----------
    api_daily_quota
        The daily API quota for the workspace.
    asession
        The SQLAlchemy async session to use for all database connections.
    content_quota
        The content quota for the workspace.
    workspace_name
        The name of the workspace to create. If not specified, then the default
        workspace name is the next available workspace ID.

    Returns
    -------
    WorkspaceDB
        The workspace object saved in the database.
    """

    if workspace_name is None:
        # Query the next available workspace ID.
        stmt = select(func.coalesce(func.max(WorkspaceDB.workspace_id), 0) + 1)
        result = await asession.execute(stmt)
        next_workspace_id = result.scalar_one()
        workspace_name = f"Workspace_{next_workspace_id}"

    # Check if workspace with same workspace name already exists.
    workspace_db = await check_if_workspace_exists(
        asession=asession, workspace_name=workspace_name
    )
    if workspace_db:
        return workspace_db

    workspace_db = WorkspaceDB(
        api_daily_quota=api_daily_quota,
        content_quota=content_quota,
        created_datetime_utc=datetime.now(timezone.utc),
        updated_datetime_utc=datetime.now(timezone.utc),
        workspace_name=workspace_name,
    )

    asession.add(workspace_db)
    await asession.commit()
    await asession.refresh(workspace_db)

    return workspace_db


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
        user = result.scalar_one()
        return user
    except NoResultFound as err:
        raise UserNotFoundError(
            f"User with username {username} does not exist."
        ) from err


async def get_user_role_in_workspace(
    *, asession: AsyncSession, user_db: UserDB, workspace_db: WorkspaceDB
) -> UserRoles | None:
    """Check if a user already exists with a specified role in the
    `UserWorkspaceRoleDB` table.

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

    stmt = (
        select(UserWorkspaceRoleDB.user_role)
        .where(
            UserWorkspaceRoleDB.user_id == user_db.user_id,
            UserWorkspaceRoleDB.workspace_id == workspace_db.workspace_id,
        )
    )
    result = await asession.execute(stmt)
    user_role = result.scalar_one_or_none()
    return user_role


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

    # Check if user with same username already exists.
    stmt = select(UserDB).where(UserDB.username == user.username)
    result = await asession.execute(stmt)
    try:
        result.one()
        raise UserAlreadyExistsError(
            f"User with username {user.username} already exists."
        )
    except NoResultFound:
        pass

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
        The async session to use for the database connection.
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


async def get_user_by_id(*, asession: AsyncSession, user_id: int) -> UserDB:
    """Retrieve a user by user ID.

    Parameters
    ----------
    asession
        The async session to use for the database connection.
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


async def get_all_users(*, asession: AsyncSession) -> Sequence[UserDB]:
    """Retrieve all users from `UserDB` database.

    Parameters
    ----------
    asession
        The async session to use for the database connection.

    Returns
    -------
    Sequence[UserDB]
        A sequence of user objects retrieved from the database.
    """

    stmt = select(UserDB)
    result = await asession.execute(stmt)
    users = result.scalars().all()
    return users


async def get_user_by_api_key(*, asession: AsyncSession, token: str) -> UserDB:
    """Retrieve a user by token.

    Parameters
    ----------
    asession
        The async session to use for the database connection.
    token
        The token to use for the query.

    Returns
    -------
    UserDB
        The user object retrieved from the database.

    Raises
    ------
    UserNotFoundError
        If the user with the specified token does not exist.
    """

    hashed_token = get_key_hash(token)

    stmt = select(UserDB).where(UserDB.hashed_api_key == hashed_token)
    result = await asession.execute(stmt)
    try:
        user = result.scalar_one()
        return user
    except NoResultFound as err:
        raise UserNotFoundError("User with given token does not exist.") from err


async def update_user_api_key(
    user_db: UserDB,
    new_api_key: str,
    asession: AsyncSession,
) -> UserDB:
    """
    Updates a user's API key
    """

    user_db.hashed_api_key = get_key_hash(new_api_key)
    user_db.api_key_first_characters = new_api_key[:5]
    user_db.api_key_updated_datetime_utc = datetime.now(timezone.utc)
    user_db.updated_datetime_utc = datetime.now(timezone.utc)

    await asession.commit()
    await asession.refresh(user_db)

    return user_db


async def get_content_quota_by_userid(
    user_id: int,
    asession: AsyncSession,
) -> int:
    """
    Retrieves a user's content quota by user_id
    """
    stmt = select(UserDB).where(UserDB.user_id == user_id)
    result = await asession.execute(stmt)
    try:
        content_quota = result.scalar_one().content_quota
        return content_quota
    except NoResultFound as err:
        raise UserNotFoundError(f"User with user_id {user_id} does not exist.") from err


async def update_user_in_db(
    user_id: int,
    user: UserCreate,
    asession: AsyncSession,
) -> UserDB:
    """
    Updates a user in the database.
    """
    user_db = UserDB(
        user_id=user_id,
        username=user.username,
        is_admin=user.is_admin,
        content_quota=user.content_quota,
        api_daily_quota=user.api_daily_quota,
        updated_datetime_utc=datetime.now(timezone.utc),
    )
    user_db = await asession.merge(user_db)

    await asession.commit()
    await asession.refresh(user_db)

    return user_db


async def is_username_valid(
    username: str,
    asession: AsyncSession,
) -> bool:
    """
    Checks if a username is valid. A new username is valid if it doesn't already exist
    in the database.
    """
    stmt = select(UserDB).where(UserDB.username == username)
    result = await asession.execute(stmt)
    try:
        result.one()
        return False
    except NoResultFound:
        return True
