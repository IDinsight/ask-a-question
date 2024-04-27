"""change response feedback schema

Revision ID: 50caccd9e332
Revises: f269c75dbf69
Create Date: 2024-04-19 10:30:54.214343

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "50caccd9e332"
down_revision: Union[str, None] = "f269c75dbf69"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "feedback", sa.Column("feedback_sentiment", sa.String(), nullable=True)
    )
    op.alter_column(
        "feedback", "feedback_text", existing_type=sa.VARCHAR(), nullable=True
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "feedback", "feedback_text", existing_type=sa.VARCHAR(), nullable=False
    )
    op.drop_column("feedback", "feedback_sentiment")
    # ### end Alembic commands ###
