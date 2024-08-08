"""test migration

Revision ID: 7e3745a3ca94
Revises: 358588881e01
Create Date: 2024-08-08 13:40:24.938318

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "7e3745a3ca94"
down_revision: Union[str, None] = "358588881e01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
