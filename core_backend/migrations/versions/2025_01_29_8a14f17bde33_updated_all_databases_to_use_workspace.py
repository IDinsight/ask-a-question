"""This script handles the migration to use `workspace_id` instead of `user_id` for the
workspace feature. In addition, standard naming conventions are also applied.

NB: This is a non-reversible migration. The downgrade process is not implemented
because it would require custom logic to handle the M:N mapping between users and
workspaces back to the 1:1 mapping.

Revision ID: 8a14f17bde33
Revises: 27fd893400f8
Create Date: 2025-01-29 12:12:07.724095

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
    """The upgrade process is as follows:

    1. Create new `workspace` table.
    2. Create new `user_workspace` table.
    3. Add `workspace_id` to all existing tables. NB: Although you could also remove
        the old `user_id` foreign key on existing tables at this step, you can't drop
        it until after the data migration is done. Thus, we remove the old `user_id`
        foreign key AFTER the data migration steps.
    4. Data migration.
        4a. Create a temporary connection/session to do inserts/updates.
        4b. Fetch all old user rows from `user` table.
        4c. Create a new workspace for each existing user and insert it into the
            `workspace` table.
        4d. For each existing user, also insert appropriate attributes into the
            `user_workspace` table.
        4e. Update the `workspace_id` attribute for existing tables for each row based
            on old `user_id`. NB: WE ASSUME THAT `user_id` IS NOT NULL IN OLD DATA.
    5. Removing old attributes.
        5a. Drop foreign key constraints with non-standard naming conventions. This
            only applies for the constraints that were manually named under revision
            465368ca2bac.
        5b. Drop indexes with non-standard naming conventions. This only applies for
           the indexes that were manually named under revision 465368ca2bac.
        5c. Drop the `user_id` column in existing tables.
        5d. Drop the following columns in `user` table that are no longer used:
            i. api_daily_quota
            ii. api_key_first_characters
            iii. api_key_updated_datetime_utc
            iv. content_quota
            v. hashed_api_key
            vi. is_admin
        5e. Finally, set `workspace_id` to NOT NULL in existing tables (now that they
            are populated).

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

    # 4a.
    connection = op.get_bind()

    # 4b.
    users = list(connection.execute(sa.text('SELECT * FROM "user"')))

    # 4c.
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
        workspace_name = f"{username}'s_Workspace"
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

        # 4d. NB: All existing users must be created as ADMIN users in their own
        # workspace. Otherwise, we would have workspaces with no admin users.
        user_role = "admin"
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

        # 4e.
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
                {"workspace_id": new_workspace_id, "old_user_id": user_id},
            )

    # 5a.
    op.drop_constraint(
        "fk_content-feedback_query_id_query", "content_feedback", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_content-feedback_content_id_content", "content_feedback", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_content_feedback_content_id_content"),
        "content_feedback",
        "content",
        ["content_id"],
        ["content_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_content_feedback_query_id_query"),
        "content_feedback",
        "query",
        ["query_id"],
        ["query_id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_content_tags_content_id_content", "content_tag", type_="foreignkey"
    )
    op.drop_constraint("fk_content_tags_tag_id_tag", "content_tag", type_="foreignkey")
    op.create_foreign_key(
        op.f("fk_content_tag_tag_id_tag"),
        "content_tag",
        "tag",
        ["tag_id"],
        ["tag_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_content_tag_content_id_content"),
        "content_tag",
        "content",
        ["content_id"],
        ["content_id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_query-response_query_id_query", "query_response", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_query_response_query_id_query"),
        "query_response",
        "query",
        ["query_id"],
        ["query_id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_query_response_content_content_id_content",
        "query_response_content",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_query_response_content_query_id_query",
        "query_response_content",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_query_response_content_query_id_query"),
        "query_response_content",
        "query",
        ["query_id"],
        ["query_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_query_response_content_content_id_content"),
        "query_response_content",
        "content",
        ["content_id"],
        ["content_id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_query-response-feedback_query_id_query",
        "query_response_feedback",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_query_response_feedback_query_id_query"),
        "query_response_feedback",
        "query",
        ["query_id"],
        ["query_id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_urgency-response_query_id_urgency-query",
        "urgency_response",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_urgency_response_query_id_urgency_query"),
        "urgency_response",
        "urgency_query",
        ["query_id"],
        ["urgency_query_id"],
        ondelete="CASCADE",
    )

    # 5b.
    op.drop_index(
        "ix_query-response-feedback_feedback_id", table_name="query_response_feedback"
    )
    op.create_index(
        op.f("ix_query_response_feedback_feedback_id"),
        "query_response_feedback",
        ["feedback_id"],
        unique=False,
    )
    op.drop_index("ix_content-feedback_feedback_id", table_name="content_feedback")
    op.create_index(
        op.f("ix_content_feedback_feedback_id"),
        "content_feedback",
        ["feedback_id"],
        unique=False,
    )
    op.drop_index("ix_urgency-query_urgency_query_id", table_name="urgency_query")
    op.create_index(
        op.f("ix_urgency_query_urgency_query_id"),
        "urgency_query",
        ["urgency_query_id"],
        unique=False,
    )
    op.drop_index(
        "ix_urgency-response_urgency_response_id", table_name="urgency_response"
    )
    op.create_index(
        op.f("ix_urgency_response_urgency_response_id"),
        "urgency_response",
        ["urgency_response_id"],
        unique=False,
    )
    op.drop_index("idx_user_id_created_datetime", table_name="query_response_content")
    op.create_index(
        "ix_workspace_id_created_datetime",
        "query_response_content",
        ["workspace_id", "created_datetime_utc"],
        unique=False,
    )
    op.drop_index("content_idx", table_name="content")
    op.create_index(
        "ix_content_embedding",
        "content",
        ["content_embedding"],
        postgresql_using="hnsw",
        postgresql_with={"M": "16", "ef_construction": "64"},
        postgresql_ops={"content_embedding": "vector_cosine_ops"},
    )

    # 5c.
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
        if table_name not in ["content", "query", "urgency_query", "urgency_rule"]:
            op.drop_constraint(
                f"fk_{table_name}_user_id_user", table_name, type_="foreignkey"
            )
        else:
            op.drop_constraint(f"fk_{table_name}_user", table_name, type_="foreignkey")
        op.drop_column(table_name, "user_id")

    # 5d.
    op.drop_column("user", "api_daily_quota")
    op.drop_column("user", "api_key_first_characters")
    op.drop_column("user", "api_key_updated_datetime_utc")
    op.drop_column("user", "content_quota")
    op.drop_column("user", "hashed_api_key")
    op.drop_column("user", "is_admin")

    # 5e.
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
        op.alter_column(
            table_name, "workspace_id", existing_type=sa.Integer(), nullable=False
        )


def downgrade() -> None:
    """NB: Each individual downgrade requires custom logic because the old version is a
    1:1 mapping between users and "workspaces" whereas the new version is an M:N
    mapping between users and workspaces. Thus, we would need custom logic for every
    single downgrade case to handle the M:N mapping back to 1:1 mapping.
    """
