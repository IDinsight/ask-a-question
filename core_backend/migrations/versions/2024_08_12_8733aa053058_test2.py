"""test2

Revision ID: 8733aa053058
Revises: 358588881e01
Create Date: 2024-08-12 10:48:01.003542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8733aa053058'
down_revision: Union[str, None] = '358588881e01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
