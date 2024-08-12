"""test2

Revision ID: b4266cea9588
Revises: 465368ca2bac
Create Date: 2024-08-12 09:51:07.130990

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4266cea9588'
down_revision: Union[str, None] = '465368ca2bac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
