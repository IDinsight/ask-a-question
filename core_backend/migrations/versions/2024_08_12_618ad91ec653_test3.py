"""test3

Revision ID: 618ad91ec653
Revises: 8733aa053058
Create Date: 2024-08-12 11:07:25.640140

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '618ad91ec653'
down_revision: Union[str, None] = '8733aa053058'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
