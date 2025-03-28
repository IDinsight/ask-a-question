"""add tags

Revision ID: b5ad153a53dc
Revises: 3228425eb430
Create Date: 2024-05-17 13:05:43.841927

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5ad153a53dc"
down_revision: Union[str, None] = "3228425eb430"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "tag",
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("tag_name", sa.String(length=50), nullable=False),
        sa.Column("created_datetime_utc", sa.DateTime(), nullable=False),
        sa.Column("updated_datetime_utc", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.user_id"],
        ),
        sa.PrimaryKeyConstraint("tag_id"),
    )
    op.create_table(
        "content_tags",
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["content.content_id"],
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tag.tag_id"],
        ),
        sa.PrimaryKeyConstraint("content_id", "tag_id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("content_tags")
    op.drop_table("tag")
    # ### end Alembic commands ###
