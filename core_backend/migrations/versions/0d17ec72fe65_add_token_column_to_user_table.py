"""add token column to user table

Revision ID: 0d17ec72fe65
Revises: cf28de217848
Create Date: 2024-04-26 17:37:01.382952

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0d17ec72fe65"
down_revision: Union[str, None] = "cf28de217848"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("user", sa.Column("retrieval_token", sa.String(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("user", "retrieval_token")
    # ### end Alembic commands ###