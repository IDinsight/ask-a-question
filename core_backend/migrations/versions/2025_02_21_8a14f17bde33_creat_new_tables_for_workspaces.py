"""Create new tables for workspaces.

This is the first migration in a three-part migration process to migrate from a 1:1
mapping between users and workspaces to an M:N mapping between users and workspaces.

NB: This migration is still reversible.

Revision ID: 8a14f17bde33
Revises: 27fd893400f8
Create Date: 2025-02-21 12:12:07.724095

Reference: https://stackoverflow.com/questions/24612395/how-do-i-execute-inserts-and-updates-in-an-alembic-upgrade-script
"""  # noqa: E501

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8a14f17bde33"  # pragma: allowlist secret
down_revision: Union[str, None] = "27fd893400f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """The workspace migration process is done in three separate migrations: the first
    migration (this one) creates the new tables and columns, the second migration does
    the data migration, and the third migration removes the old columns, constraints,
    etc.

    For this migration, the process is as follows:

    1. Create new `workspace` table.
    2. Create new `user_workspace` table.
    3. Add `workspace_id` to all existing tables. NB: Although you could also remove
        the old `user_id` foreign key on existing tables at this step, you can't drop
        it until after the data migration is done. Thus, we remove the old `user_id`
        foreign key AFTER the data migration steps.

    Other points:
    1. Since `Base.metadata` defines naming conventions prior to this migration,
        constraints should be named automatically.
    """

    # 1.
    op.create_table(
        "workspace",
        sa.Column("api_daily_quota", sa.Integer(), nullable=True),
        sa.Column("api_key_first_characters", sa.String(length=5), nullable=True),
        sa.Column(
            "api_key_updated_datetime_utc", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("content_quota", sa.Integer(), nullable=True),
        sa.Column("created_datetime_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hashed_api_key", sa.String(96), nullable=True, unique=True),
        sa.Column("updated_datetime_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("workspace_id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("workspace_name", sa.String(), nullable=False, unique=True),
    )

    # 2,
    user_roles_enum = sa.Enum("ADMIN", "READ_ONLY", name="userroles", native_enum=False)
    user_roles_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "user_workspace",
        sa.Column("created_datetime_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "default_workspace",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("updated_datetime_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("user.user_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("user_role", user_roles_enum, nullable=False),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    # 3. NB: Keep `workspace_id` as nullable at this point. We will set it to
    # non-nullable at the end.
    for table_name in [
        "content",
        "query",
        "query_response",
        "query_response_content",
        "query_response_feedback",
        "content_feedback",
        "tag",
        "urgency_query",
        "urgency_response",
        "urgency_rule",
    ]:
        op.add_column(
            table_name,
            sa.Column(
                "workspace_id",
                sa.Integer(),
                sa.ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    """Reverse the changes made in the upgrade function as follows:

    1. Remove `workspace_id` column from all existing tables.
    2. Drop `user_workspace` table.
    3. Drop `userroles` enum type.
    4. Drop `workspace` table.
    """

    # 1.
    for table_name in [
        "content",
        "query",
        "query_response",
        "query_response_content",
        "query_response_feedback",
        "content_feedback",
        "tag",
        "urgency_query",
        "urgency_response",
        "urgency_rule",
    ]:
        op.drop_column(table_name, "workspace_id")

    # 2.
    op.drop_table("user_workspace")

    # 3.
    user_roles_enum = sa.Enum("ADMIN", "READ_ONLY", name="userroles", native_enum=False)
    user_roles_enum.drop(op.get_bind(), checkfirst=True)

    # 4.
    op.drop_table("workspace")
