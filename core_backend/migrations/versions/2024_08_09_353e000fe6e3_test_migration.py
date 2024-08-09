"""test migration

Revision ID: 353e000fe6e3
Revises: 358588881e01
Create Date: 2024-08-09 08:24:07.672376

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '353e000fe6e3'
down_revision: Union[str, None] = '358588881e01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
