"""another test migration

Revision ID: 0997fb8abab4
Revises: 358588881e01
Create Date: 2024-08-08 13:50:31.997204

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0997fb8abab4"
down_revision: Union[str, None] = "358588881e01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
