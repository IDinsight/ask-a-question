"""change session_id to string

Revision ID: 1bbcc2584fde
Revises: c571cf9aae63
Create Date: 2024-08-26 19:40:08.259316

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1bbcc2584fde"  # pragma: allowlist secret
down_revision: Union[str, None] = "c571cf9aae63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

tables_with_session_id = [
    "query",
    "query_response",
    "query_response_feedback",
    "query_response_content",
    "content_feedback",
]


def upgrade() -> None:
    for table in tables_with_session_id:
        op.alter_column(
            table, "session_id", existing_type=sa.Integer(), type_=sa.String()
        )


def downgrade() -> None:
    for table in tables_with_session_id:
        # TODO: if the session_id can't be casted, set it to null
        op.alter_column(
            table, "session_id", existing_type=sa.String(), type_=sa.Integer()
        )
