"""Merge Response and ResponseError DBs

Revision ID: 9d0519332fdd
Revises: 6fd6bcd063ff
Create Date: 2024-07-25 14:39:09.479194

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9d0519332fdd"
down_revision: Union[str, None] = "6fd6bcd063ff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # add is_error column to query-response (not nullable)
    op.add_column("query-response", sa.Column("is_error", sa.Boolean(), nullable=True))
    op.execute('UPDATE "query-response" SET is_error = False')
    op.alter_column(
        "query-response", "is_error", existing_type=sa.Boolean(), nullable=False
    )

    # add debug_info column to query-response (not nullable)
    op.add_column("query-response", sa.Column("debug_info", sa.JSON(), nullable=True))
    op.execute("UPDATE \"query-response\" SET debug_info = '{}'::json")
    op.alter_column(
        "query-response", "debug_info", existing_type=sa.JSON(), nullable=False
    )

    # add error_type, and error_message columns to query-response (nullable)
    op.add_column("query-response", sa.Column("error_type", sa.String(), nullable=True))
    op.add_column(
        "query-response", sa.Column("error_message", sa.String(), nullable=True)
    )

    # move data from query-response-error to query-response
    op.execute(
        'INSERT INTO "query-response" (query_id, search_results, llm_response, '
        "response_datetime_utc, is_error, debug_info, error_type, error_message) "
        "SELECT query_id,  '{}'::json, null, error_datetime_utc, true, debug_info, "
        'error_type, error_message FROM "query-response-error"'
    )

    op.drop_table("query-response-error")
    # ### end Alembic commands ###


def downgrade() -> None:
    # create query-response-error table and move data from query-response
    op.create_table(
        "query-response-error",
        sa.Column("error_id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("query_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("error_message", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("error_type", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            "error_datetime_utc",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "debug_info",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["query_id"], ["query.query_id"], name="query-response-error_query_id_fkey"
        ),
        sa.PrimaryKeyConstraint("error_id", name="query-response-error_pkey"),
    )
    op.execute(
        'INSERT INTO "query-response-error" (query_id, error_message, error_type, '
        "error_datetime_utc, debug_info) "
        "SELECT query_id, error_message, error_type, response_datetime_utc, debug_info "
        'FROM "query-response" WHERE is_error = true'
    )

    # drop columns from query-response
    op.drop_column("query-response", "error_message")
    op.drop_column("query-response", "error_type")
    op.drop_column("query-response", "is_error")
    op.drop_column("query-response", "debug_info")
