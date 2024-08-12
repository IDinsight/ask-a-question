"""test2

Revision ID: 8c7ca3908a12
Revises: 358588881e01
Create Date: 2024-08-12 09:56:18.566369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c7ca3908a12'
down_revision: Union[str, None] = '358588881e01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
