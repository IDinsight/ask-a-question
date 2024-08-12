"""test1

Revision ID: 3d49a66a01fd
Revises: 358588881e01
Create Date: 2024-08-12 10:29:08.132359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d49a66a01fd'
down_revision: Union[str, None] = '358588881e01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
