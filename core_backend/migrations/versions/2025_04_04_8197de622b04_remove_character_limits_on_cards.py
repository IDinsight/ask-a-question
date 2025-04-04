"""remove character limits on cards

Revision ID: 8197de622b04
Revises: b1daed9f42c4
Create Date: 2025-04-04 07:07:41.560536

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8197de622b04"  # pragma: allowlist secret
down_revision: Union[str, None] = "b1daed9f42c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alter the content_text column to use TEXT type instead of VARCHAR(2000)
    op.alter_column(
        "content",
        "content_text",
        existing_type=sa.VARCHAR(2000),
        type_=sa.Text(),
        existing_nullable=True,
    )

    # If you also need to modify content_title
    op.alter_column(
        "content",
        "content_title",
        existing_type=sa.VARCHAR(150),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Revert back to VARCHAR(2000) if needed
    op.alter_column(
        "content",
        "content_text",
        existing_type=sa.Text(),
        type_=sa.VARCHAR(2000),
        existing_nullable=True,
    )

    op.alter_column(
        "content",
        "content_title",
        existing_type=sa.Text(),
        type_=sa.VARCHAR(150),
        existing_nullable=True,
    )
