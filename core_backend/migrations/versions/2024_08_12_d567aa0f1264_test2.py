"""test2

Revision ID: d567aa0f1264
Revises: 465368ca2bac
Create Date: 2024-08-12 10:43:41.331710

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd567aa0f1264'
down_revision: Union[str, None] = '465368ca2bac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
