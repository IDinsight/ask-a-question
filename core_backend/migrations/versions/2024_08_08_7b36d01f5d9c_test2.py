"""test2

Revision ID: 7b36d01f5d9c
Revises: 358588881e01
Create Date: 2024-08-08 14:06:42.585618

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "7b36d01f5d9c"
down_revision: Union[str, None] = "358588881e01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Some upgrade"""
    pass


def downgrade() -> None:
    """Some downgrade"""
    pass
