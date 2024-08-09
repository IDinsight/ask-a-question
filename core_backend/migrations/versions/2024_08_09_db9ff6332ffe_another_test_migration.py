"""another test migration

Revision ID: db9ff6332ffe
Revises: f8e041a042dc
Create Date: 2024-08-09 09:18:03.668742

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db9ff6332ffe'
down_revision: Union[str, None] = 'f8e041a042dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
