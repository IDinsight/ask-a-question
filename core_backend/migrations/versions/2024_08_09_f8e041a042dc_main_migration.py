"""main migration

Revision ID: f8e041a042dc
Revises: 358588881e01
Create Date: 2024-08-09 08:17:23.808625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8e041a042dc'
down_revision: Union[str, None] = '358588881e01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
