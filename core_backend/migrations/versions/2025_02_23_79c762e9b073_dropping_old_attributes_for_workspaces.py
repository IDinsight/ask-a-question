"""Dropping old attributes for workspaces.

This is the third migration in a three-part process to migrate from a 1:1 mapping
between users and workspaces to an M:N mapping between users and workspaces.

NB: This migration is NOT reversible.

Revision ID: 79c762e9b073
Revises: 10b63dea7654
Create Date: 2025-02-23 14:32:29.756567

Reference: https://stackoverflow.com/questions/24612395/how-do-i-execute-inserts-and-updates-in-an-alembic-upgrade-script
"""  # noqa: E501

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "79c762e9b073"  # pragma: allowlist secret
down_revision: Union[str, None] = "10b63dea7654"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """The workspace migration process is done in three separate migrations: the first
    migration creates the new tables and columns, the second migration does the data
    migration, and the third migration (this one) removes the old columns, constraints,
    etc.

    For this migration, the process is as follows:

    1. Drop foreign key constraints with non-standard naming conventions. This only
        applies for the constraints that were manually named under revision
        465368ca2bac.
    2. Drop indexes with non-standard naming conventions. This only applies for the
        indexes that were manually named under revision 465368ca2bac.
    3. Drop the `user_id` column in existing tables.
    4. Drop the following columns in `user` table that are no longer used:
        3a. api_daily_quota
        3b. api_key_first_characters
        3c. api_key_updated_datetime_utc
        3d. content_quota
        3e. hashed_api_key
        3f. is_admin
    5. Finally, set `workspace_id` to NOT NULL in existing tables (now that they are
        populated).

    Other points:
    1. Since `Base.metadata` defines naming conventions prior to this migration,
        constraints should be named automatically.
    """

    # 1.
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

    # 2.
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

    # 3.
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

    # 4.
    op.drop_column("user", "api_daily_quota")
    op.drop_column("user", "api_key_first_characters")
    op.drop_column("user", "api_key_updated_datetime_utc")
    op.drop_column("user", "content_quota")
    op.drop_column("user", "hashed_api_key")
    op.drop_column("user", "is_admin")

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
        op.alter_column(
            table_name, "workspace_id", existing_type=sa.Integer(), nullable=False
        )


def downgrade() -> None:
    """NB: Each individual downgrade requires custom logic because the old version is a
    1:1 mapping between users and "workspaces" whereas the new version is an M:N
    mapping between users and workspaces. Thus, we would need custom logic for every
    single downgrade case to handle the M:N mapping back to 1:1 mapping.
    """
