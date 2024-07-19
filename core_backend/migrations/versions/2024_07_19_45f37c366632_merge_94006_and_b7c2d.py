"""Merge 94006 and b7c2d

Revision ID: 45f37c366632
Revises: 9400641b16d3, b7c2d860ba50
Create Date: 2024-07-19 08:24:13.952006

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "45f37c366632"
down_revision: tuple[str, str] = ("9400641b16d3", "b7c2d860ba50")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
