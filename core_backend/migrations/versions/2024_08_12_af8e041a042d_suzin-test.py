"""suzin-test

Revision ID: af8e041a042d
Revises: 358588881e01
Create Date: 2024-08-09 08:17:23.808625

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "af8e041a042d"  # pragma: allowlist secret
down_revision: Union[str, None] = "358588881e01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
