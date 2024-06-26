"""empty message

Revision ID: 7a68f045e8d3
Revises: 29b5ffa97758
Create Date: 2024-06-26 12:41:46.706891

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a68f045e8d3"
down_revision: Union[str, None] = "29b5ffa97758"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("content", "content_language")


def downgrade() -> None:
    op.add_column("content", sa.Column("content_language", sa.String(), nullable=False))
    op.execute("UPDATE content SET content_language = 'ENGLISH'")
