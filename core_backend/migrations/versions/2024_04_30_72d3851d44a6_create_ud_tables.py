"""Create UD tables

Revision ID: 72d3851d44a6
Revises: e8ddc3de6210
Create Date: 2024-04-30 09:04:46.065462

"""

from typing import Sequence, Union

import pgvector
import sqlalchemy as sa
from alembic import op
from app.config import PGVECTOR_VECTOR_SIZE

# revision identifiers, used by Alembic.
revision: str = "72d3851d44a6"
down_revision: Union[str, None] = "e8ddc3de6210"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "urgency-query",
        sa.Column("urgency_query_id", sa.Integer(), nullable=False),
        sa.Column("message_text", sa.String(), nullable=False),
        sa.Column("message_datetime_utc", sa.DateTime(), nullable=False),
        sa.Column("feedback_secret_key", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("urgency_query_id"),
    )
    op.create_index(
        op.f("ix_urgency-query_urgency_query_id"),
        "urgency-query",
        ["urgency_query_id"],
        unique=False,
    )
    op.create_table(
        "urgency-rule",
        sa.Column("urgency_rule_id", sa.Integer(), nullable=False),
        sa.Column("urgency_rule_text", sa.String(), nullable=False),
        sa.Column(
            "urgency_rule_vector",
            pgvector.sqlalchemy.Vector(dim=int(PGVECTOR_VECTOR_SIZE)),
            nullable=False,
        ),
        sa.Column("urgency_rule_metadata", sa.JSON(), nullable=True),
        sa.Column("created_datetime_utc", sa.DateTime(), nullable=False),
        sa.Column("updated_datetime_utc", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("urgency_rule_id"),
    )
    op.create_table(
        "urgency-response",
        sa.Column("urgency_response_id", sa.Integer(), nullable=False),
        sa.Column("is_urgent", sa.Boolean(), nullable=False),
        sa.Column("failed_rules", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("query_id", sa.Integer(), nullable=False),
        sa.Column("response_datetime_utc", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["query_id"],
            ["urgency-query.urgency_query_id"],
        ),
        sa.PrimaryKeyConstraint("urgency_response_id"),
    )
    op.create_index(
        op.f("ix_urgency-response_urgency_response_id"),
        "urgency-response",
        ["urgency_response_id"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_urgency-response_urgency_response_id"), table_name="urgency-response"
    )
    op.drop_table("urgency-response")
    op.drop_table("urgency-rule")
    op.drop_index(op.f("ix_urgency-query_urgency_query_id"), table_name="urgency-query")
    op.drop_table("urgency-query")
    # ### end Alembic commands ###
