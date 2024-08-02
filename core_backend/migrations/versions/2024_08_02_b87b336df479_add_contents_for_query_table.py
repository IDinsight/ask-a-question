"""add contents for query table

Revision ID: b87b336df479
Revises: 9d0519332fdd
Create Date: 2024-08-02 09:44:31.724254

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b87b336df479"
down_revision: Union[str, None] = "a5a6db9eca6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "query_response_content",
        sa.Column("content_for_query_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("query_id", sa.Integer(), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("created_datetime_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["content.content_id"],
        ),
        sa.ForeignKeyConstraint(
            ["query_id"],
            ["query.query_id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.user_id"],
        ),
        sa.PrimaryKeyConstraint("content_for_query_id"),
    )
    op.create_index(
        "idx_user_id_created_datetime",
        "query_response_content",
        ["user_id", "created_datetime_utc"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("idx_user_id_created_datetime", table_name="query_response_content")
    op.drop_table("query_response_content")
    # ### end Alembic commands ###