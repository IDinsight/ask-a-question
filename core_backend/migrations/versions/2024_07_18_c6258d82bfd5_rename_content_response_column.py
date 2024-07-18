"""rename content_response column to search_results

Revision ID: c6258d82bfd5
Revises: 30549f0b428a
Create Date: 2024-07-18 01:35:15.235945

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6258d82bfd5"
down_revision: Union[str, None] = "30549f0b428a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "query-response",
        "content_response",
        new_column_name="search_results",
    )


def downgrade() -> None:
    op.alter_column(
        "query-response",
        "search_results",
        new_column_name="content_response",
    )
