"""drop whatsapp tables

Revision ID: 30549f0b428a
Revises: 4d3f01bf891f
Create Date: 2024-07-17 20:16:40.576363

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "30549f0b428a"
down_revision: Union[str, None] = "4d3f01bf891f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("whatsapp_responses")
    op.drop_table("whatsapp_incoming_messages")


def downgrade() -> None:
    op.create_table(
        "whatsapp_incoming_messages",
        sa.Column("incoming_id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column(
            "msg_id_from_whatsapp", sa.VARCHAR(), autoincrement=False, nullable=False
        ),
        sa.Column("phone_number", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("message", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("phonenumber_id", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            "incoming_datetime_utc",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("incoming_id", name="whatsapp_incoming_messages_pkey"),
    )

    op.create_table(
        "whatsapp_responses",
        sa.Column("response_id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("incoming_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("response", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column(
            "response_datetime_utc",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("response_status", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(
            ["incoming_id"],
            ["whatsapp_incoming_messages.incoming_id"],
            name="whatsapp_responses_incoming_id_fkey",
        ),
        sa.PrimaryKeyConstraint("response_id", name="whatsapp_responses_pkey"),
    )
