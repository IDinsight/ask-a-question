"""test2 revision.

Revision ID: 34b1899cd0aa
Revises: 358588881e01
Create Date: 2024-08-12 09:21:11.024111

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "34b1899cd0aa"
down_revision: Union[str, None] = "358588881e01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
