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
from sqlalchemy.engine.reflection import Inspector

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

    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    # 1.
    table_name = "content_feedback"
    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys(table_name)}
    old_fk_names = [
        "fk_content-feedback_query_id_query",
        "fk_content-feedback_content_id_content",
    ]
    for fk_name in old_fk_names:
        if fk_name in existing_fks:
            op.drop_constraint(fk_name, table_name, type_="foreignkey")
    if "fk_content_feedback_content_id_content" not in existing_fks:
        op.create_foreign_key(
            op.f("fk_content_feedback_content_id_content"),
            table_name,
            "content",
            ["content_id"],
            ["content_id"],
            ondelete="CASCADE",
        )
    if "fk_content_feedback_query_id_query" not in existing_fks:
        op.create_foreign_key(
            op.f("fk_content_feedback_query_id_query"),
            table_name,
            "query",
            ["query_id"],
            ["query_id"],
            ondelete="CASCADE",
        )

    table_name = "content_tag"
    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys(table_name)}
    old_fk_names = ["fk_content_tags_content_id_content", "fk_content_tags_tag_id_tag"]
    for fk_name in old_fk_names:
        if fk_name in existing_fks:
            op.drop_constraint(fk_name, table_name, type_="foreignkey")
    if "fk_content_tag_tag_id_tag" not in existing_fks:
        op.create_foreign_key(
            op.f("fk_content_tag_tag_id_tag"),
            table_name,
            "tag",
            ["tag_id"],
            ["tag_id"],
            ondelete="CASCADE",
        )
    if "fk_content_tag_content_id_content" not in existing_fks:
        op.create_foreign_key(
            op.f("fk_content_tag_content_id_content"),
            table_name,
            "content",
            ["content_id"],
            ["content_id"],
            ondelete="CASCADE",
        )

    table_name = "query_response"
    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys(table_name)}
    old_fk_names = ["fk_query-response_query_id_query"]
    for fk_name in old_fk_names:
        if fk_name in existing_fks:
            op.drop_constraint(fk_name, table_name, type_="foreignkey")
    if "fk_query_response_query_id_query" not in existing_fks:
        op.create_foreign_key(
            op.f("fk_query_response_query_id_query"),
            table_name,
            "query",
            ["query_id"],
            ["query_id"],
            ondelete="CASCADE",
        )

    table_name = "query_response_content"
    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys(table_name)}
    if "fk_query_response_content_query_id_query" in existing_fks:
        op.drop_constraint(
            "fk_query_response_content_query_id_query", table_name, type_="foreignkey"
        )
        op.create_foreign_key(
            op.f("fk_query_response_content_query_id_query"),
            table_name,
            "query",
            ["query_id"],
            ["query_id"],
            ondelete="CASCADE",
        )
    if "fk_query_response_content_content_id_content" in existing_fks:
        op.drop_constraint(
            "fk_query_response_content_content_id_content",
            table_name,
            type_="foreignkey",
        )
        op.create_foreign_key(
            op.f("fk_query_response_content_content_id_content"),
            table_name,
            "content",
            ["content_id"],
            ["content_id"],
            ondelete="CASCADE",
        )

    table_name = "query_response_feedback"
    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys(table_name)}
    old_fk_names = ["fk_query-response-feedback_query_id_query"]
    for fk_name in old_fk_names:
        if fk_name in existing_fks:
            op.drop_constraint(fk_name, table_name, type_="foreignkey")
    if "fk_query_response_feedback_query_id_query" not in existing_fks:
        op.create_foreign_key(
            op.f("fk_query_response_feedback_query_id_query"),
            table_name,
            "query",
            ["query_id"],
            ["query_id"],
            ondelete="CASCADE",
        )

    table_name = "urgency_response"
    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys(table_name)}
    old_fk_names = ["fk_urgency-response_query_id_urgency-query"]
    for fk_name in old_fk_names:
        if fk_name in existing_fks:
            op.drop_constraint(fk_name, table_name, type_="foreignkey")
    if "fk_urgency_response_query_id_urgency_query" not in existing_fks:
        op.create_foreign_key(
            op.f("fk_urgency_response_query_id_urgency_query"),
            table_name,
            "urgency_query",
            ["query_id"],
            ["urgency_query_id"],
            ondelete="CASCADE",
        )

    # 2.
    table_name = "query_response_feedback"
    existing_indexes = {ix["name"] for ix in inspector.get_indexes(table_name)}
    old_ix_names = ["ix_query-response-feedback_feedback_id"]
    for ix_name in old_ix_names:
        if ix_name in existing_indexes:
            op.drop_index(ix_name, table_name=table_name)
    if "ix_query_response_feedback_feedback_id" not in existing_indexes:
        op.create_index(
            op.f("ix_query_response_feedback_feedback_id"),
            table_name,
            ["feedback_id"],
            unique=False,
        )

    table_name = "content_feedback"
    existing_indexes = {ix["name"] for ix in inspector.get_indexes(table_name)}
    old_ix_names = ["ix_content-feedback_feedback_id"]
    for ix_name in old_ix_names:
        if ix_name in existing_indexes:
            op.drop_index(ix_name, table_name=table_name)
    if "ix_content_feedback_feedback_id" not in existing_indexes:
        op.create_index(
            op.f("ix_content_feedback_feedback_id"),
            table_name,
            ["feedback_id"],
            unique=False,
        )

    table_name = "urgency_query"
    existing_indexes = {ix["name"] for ix in inspector.get_indexes(table_name)}
    old_ix_names = ["ix_urgency-query_urgency_query_id"]
    for ix_name in old_ix_names:
        if ix_name in existing_indexes:
            op.drop_index(ix_name, table_name=table_name)
    if "ix_urgency_query_urgency_query_id" not in existing_indexes:
        op.create_index(
            op.f("ix_urgency_query_urgency_query_id"),
            table_name,
            ["urgency_query_id"],
            unique=False,
        )

    table_name = "urgency_response"
    existing_indexes = {ix["name"] for ix in inspector.get_indexes(table_name)}
    old_ix_names = ["ix_urgency-response_urgency_response_id"]
    for ix_name in old_ix_names:
        if ix_name in existing_indexes:
            op.drop_index(ix_name, table_name=table_name)
    if "ix_urgency_response_urgency_response_id" not in existing_indexes:
        op.create_index(
            op.f("ix_urgency_response_urgency_response_id"),
            table_name,
            ["urgency_response_id"],
            unique=False,
        )

    table_name = "query_response_content"
    existing_indexes = {ix["name"] for ix in inspector.get_indexes(table_name)}
    old_ix_names = ["idx_user_id_created_datetime"]
    for ix_name in old_ix_names:
        if ix_name in existing_indexes:
            op.drop_index(ix_name, table_name=table_name)
    if "ix_workspace_id_created_datetime" not in existing_indexes:
        op.create_index(
            "ix_workspace_id_created_datetime",
            table_name,
            ["workspace_id", "created_datetime_utc"],
            unique=False,
        )

    table_name = "content"
    existing_indexes = {ix["name"] for ix in inspector.get_indexes(table_name)}
    old_ix_names = ["content_idx"]
    for ix_name in old_ix_names:
        if ix_name in existing_indexes:
            op.drop_index(ix_name, table_name=table_name)
    if "ix_content_embedding" not in existing_indexes:
        op.create_index(
            "ix_content_embedding",
            table_name,
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
            existing_fks = {fk["name"] for fk in inspector.get_foreign_keys(table_name)}
            old_fk_name = f"fk_{table_name}_user_id_user"
            if old_fk_name in existing_fks:
                op.drop_constraint(old_fk_name, table_name, type_="foreignkey")
        else:
            existing_fks = {fk["name"] for fk in inspector.get_foreign_keys(table_name)}
            old_fk_name = f"fk_{table_name}_user"
            if old_fk_name in existing_fks:
                op.drop_constraint(old_fk_name, table_name, type_="foreignkey")
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
