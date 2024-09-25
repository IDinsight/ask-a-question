"""Add is_admin to userdb

Revision ID: 6351eefb1e6b
Revises: c571cf9aae63
Create Date: 2024-09-25 11:43:35.871027

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6351eefb1e6b"
down_revision: Union[str, None] = "c571cf9aae63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("user", sa.Column("is_admin", sa.Boolean(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("user", "is_admin")
    # ### end Alembic commands ###
