"""change content table's user_id to ForeignKey

Revision ID: 55cf4d21158b
Revises: cf28de217848
Create Date: 2024-04-27 10:18:24.482441

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "55cf4d21158b"
down_revision: Union[str, None] = "cf28de217848"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key(None, "content", "user", ["user_id"], ["user_id"])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "content", type_="foreignkey")
    # ### end Alembic commands ###
