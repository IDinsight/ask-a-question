"""suzin-test

Revision ID: af8e041a042d
Revises: 465368ca2bac
Create Date: 2024-08-12 08:17:23.808625

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "af8e041a042d"  # pragma: allowlist secret
down_revision: Union[str, None] = "465368ca2bac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
