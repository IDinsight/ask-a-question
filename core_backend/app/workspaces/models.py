"""SQLAlchemy ORM models for the `workspaces` feature."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.users.models import UserDB, UserWorkspaceDB


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
    doc_language: Mapped[str] = mapped_column(String, nullable=False)
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
