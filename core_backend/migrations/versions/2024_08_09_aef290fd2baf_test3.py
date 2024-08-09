"""test3

Revision ID: aef290fd2baf
Revises: 008fa3fd5c05
Create Date: 2024-08-09 07:59:18.318547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aef290fd2baf'
down_revision: Union[str, None] = '008fa3fd5c05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
