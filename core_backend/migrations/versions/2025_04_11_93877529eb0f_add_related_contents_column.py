"""Add related contents column

Revision ID: 93877529eb0f
Revises: 8197de622b04
Create Date: 2025-04-11 14:05:00.867689

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "93877529eb0f"  # pragma: allowlist secret
down_revision: Union[str, None] = "8197de622b04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "content",
        sa.Column(
            "related_contents_id",
            postgresql.ARRAY(sa.Integer()),
            nullable=False,
            server_default=sa.text("ARRAY[]::INTEGER[]"),
        ),
    )
    op.execute(
        "UPDATE content SET related_contents_id = ARRAY[]::INTEGER[] "
        "WHERE related_contents_id IS NULL"
    )

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("content", "related_contents_id")
    # ### end Alembic commands ###
