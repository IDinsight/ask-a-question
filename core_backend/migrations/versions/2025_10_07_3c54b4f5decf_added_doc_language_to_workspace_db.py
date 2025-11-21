"""Added doc_language to workspace DB.

Revision ID: 3c54b4f5decf
Revises: 93877529eb0f
Create Date: 2025-10-07 09:23:12.056210

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c54b4f5decf"
down_revision: Union[str, None] = "93877529eb0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workspace", sa.Column("doc_language", sa.String(), nullable=True))
    # Set default value for existing rows
    op.execute(
        "UPDATE workspace SET doc_language = 'ENGLISH' WHERE doc_language IS NULL"
    )
    op.alter_column("workspace", "doc_language", nullable=False)


def downgrade() -> None:
    op.drop_column("workspace", "doc_language")
