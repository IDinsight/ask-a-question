"""test migration

Revision ID: 1c526a58080d
Revises: 465368ca2bac
Create Date: 2024-08-12 07:41:22.034617

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "1c526a58080d"
down_revision: Union[str, None] = "465368ca2bac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
