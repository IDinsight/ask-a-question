"""create query-response table

Revision ID: cda1098017b5
Revises: 42fe00da1c48
Create Date: 2023-10-12 10:24:41.889026

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cda1098017b5"
down_revision: Union[str, None] = "42fe00da1c48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "query-response",
        sa.Column("response_id", sa.Integer(), nullable=False),
        sa.Column("query_id", sa.Integer(), nullable=False),
        sa.Column("content_response", sa.JSON(), nullable=False),
        sa.Column("llm_response", sa.String(), nullable=True),
        sa.Column("response_datetime_utc", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["query_id"],
            ["query.query_id"],
        ),
        sa.PrimaryKeyConstraint("response_id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("query-response")
    # ### end Alembic commands ###
