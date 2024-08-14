"""NEW_MIGRATION_FOR_TESTING

Revision ID: 7d9ce8c31781
Revises: 7192d62a0b83
Create Date: 2024-08-14 17:35:52.459271

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "7d9ce8c31781"
down_revision: Union[str, None] = "7192d62a0b83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
