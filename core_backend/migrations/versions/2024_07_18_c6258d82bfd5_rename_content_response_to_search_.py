"""rename content_response to search_results

Revision ID: c6258d82bfd5
Revises: 30549f0b428a
Create Date: 2024-07-18 01:35:15.235945

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision: str = "c6258d82bfd5"
down_revision: Union[str, None] = "30549f0b428a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the new column search_results
    op.add_column(
        "query-response", sa.Column("search_results", sa.JSON(), nullable=True)
    )

    # Transfer data from content_response to search_results
    query_response = table(
        "query-response",
        column("content_response", sa.JSON),
        column("search_results", sa.JSON),
    )
    conn = op.get_bind()
    conn.execute(
        query_response.update().values(search_results=query_response.c.content_response)
    )

    # Drop the content_response column
    op.drop_column("query-response", "content_response")

    # Make search_results non-nullable after data transfer
    op.alter_column("query-response", "search_results", nullable=False)


def downgrade() -> None:
    # Add the content_response column back
    op.add_column(
        "query-response",
        sa.Column(
            "content_response", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
    )

    # Transfer data from search_results to content_response
    query_response = table(
        "query-response",
        column("content_response", sa.JSON),
        column("search_results", sa.JSON),
    )
    conn = op.get_bind()
    conn.execute(
        query_response.update().values(content_response=query_response.c.search_results)
    )

    # Drop the search_results column
    op.drop_column("query-response", "search_results")

    # Make content_response non-nullable after data transfer
    op.alter_column("query-response", "content_response", nullable=False)
