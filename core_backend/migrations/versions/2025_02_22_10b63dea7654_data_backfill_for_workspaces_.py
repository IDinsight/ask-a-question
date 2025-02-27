"""Data backfill for workspaces.

This is the second migration in a three-part process to migrate from a 1:1 mapping
between users and workspaces to an M:N mapping between users and workspaces.

NB: This migration is NOT reversible.

Revision ID: 10b63dea7654
Revises: 8a14f17bde33
Create Date: 2025-02-22 14:33:22.870690

Reference: https://stackoverflow.com/questions/24612395/how-do-i-execute-inserts-and-updates-in-an-alembic-upgrade-script
"""  # noqa: E501

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "10b63dea7654"  # pragma: allowlist secret
down_revision: Union[str, None] = "8a14f17bde33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """The upgrade process is done in three separate migrations: the first migration
    creates the new tables and columns, the second migration (this one) does the data
    migration, and the third migration removes the old columns, constraints, etc.

    For this migration, the process is as follows:

    1. Create a temporary connection/session to do inserts/updates.
    2. Fetch all old user rows from `user` table.
    3. Create a new workspace for each existing user and insert it into the
        `workspace` table.
    4. For each existing user, also insert appropriate attributes into the
        `user_workspace` table.
    5. Update the `workspace_id` attribute for existing tables for each row based
        on old `user_id`. NB: WE ASSUME THAT `user_id` IS NOT NULL IN OLD DATA.

    Other points:
    1. Since `Base.metadata` defines naming conventions prior to this migration,
        constraints should be named automatically.
    """

    # 1
    connection = op.get_bind()

    # 2
    users = connection.execute(sa.text('SELECT * FROM "user"')).mappings()

    # 3
    for row in users:
        api_daily_quota = row["api_daily_quota"]
        api_key_first_characters = row["api_key_first_characters"]
        api_key_updated_datetime_utc = row["api_key_updated_datetime_utc"]
        content_quota = row["content_quota"]
        created_datetime_utc = row["created_datetime_utc"]
        hashed_api_key = row["hashed_api_key"]
        # is_admin = row["is_admin"]  # Not needed for data migration
        user_id = row["user_id"]
        username = row["username"]
        updated_datetime_utc = row["updated_datetime_utc"]

        # Insert into `workspace` table.
        assert user_id is not None, f"{username = } {user_id = }"
        workspace_name = f"{username}'s Workspace"
        result = connection.execute(
            sa.text(
                """
                INSERT INTO workspace (
                    api_daily_quota,
                    api_key_first_characters,
                    api_key_updated_datetime_utc,
                    content_quota,
                    created_datetime_utc,
                    hashed_api_key,
                    updated_datetime_utc,
                    workspace_name
                )
                VALUES (
                    :api_daily_quota,
                    :api_key_first_characters,
                    :api_key_updated_datetime_utc,
                    :content_quota,
                    :created_datetime_utc,
                    :hashed_api_key,
                    :updated_datetime_utc,
                    :workspace_name
                )
                RETURNING workspace_id
                """
            ),
            {
                "api_daily_quota": api_daily_quota,
                "api_key_first_characters": api_key_first_characters,
                "api_key_updated_datetime_utc": api_key_updated_datetime_utc,
                "content_quota": content_quota,
                "created_datetime_utc": created_datetime_utc,
                "hashed_api_key": hashed_api_key,
                "updated_datetime_utc": updated_datetime_utc,
                "workspace_name": workspace_name,
            },
        )
        new_workspace_id = result.fetchone()[0]

        # 4. NB: All existing users must be created as ADMIN users in their own
        # workspace. Otherwise, we would have workspaces with no admin users.
        user_role = "ADMIN"
        connection.execute(
            sa.text(
                """
                INSERT INTO user_workspace
                (
                    created_datetime_utc,
                    default_workspace,
                    updated_datetime_utc,
                    user_id,
                    user_role,
                    workspace_id
                )
                VALUES (
                    :created_datetime_utc,
                    :default_workspace,
                    :updated_datetime_utc,
                    :user_id,
                    :user_role,
                    :workspace_id
                )
                """
            ),
            {
                "created_datetime_utc": created_datetime_utc,
                "default_workspace": True,
                "updated_datetime_utc": updated_datetime_utc,
                "user_id": user_id,
                "user_role": user_role,
                "workspace_id": new_workspace_id,
            },
        )

        # 5.
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
            connection.execute(
                sa.text(
                    f"""
                        UPDATE {table_name}
                        SET workspace_id = :new_workspace_id
                        WHERE user_id = :old_user_id
                    """
                ),
                {"new_workspace_id": new_workspace_id, "old_user_id": user_id},
            )


def downgrade() -> None:
    """NB: Each individual downgrade requires custom logic because the old version is a
    1:1 mapping between users and "workspaces" whereas the new version is an M:N
    mapping between users and workspaces. Thus, we would need custom logic for every
    single downgrade case to handle the M:N mapping back to 1:1 mapping.
    """
