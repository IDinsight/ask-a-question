"""SQLAlchemy ORM models for the `users` feature."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.users.schemas import (
    UserRoles,
)

if TYPE_CHECKING:
    from app.workspaces.models import WorkspaceDB


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
    # Argon2 hashes are ~97 chars (legacy SHA-256 ones were 96); leave headroom.
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
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
