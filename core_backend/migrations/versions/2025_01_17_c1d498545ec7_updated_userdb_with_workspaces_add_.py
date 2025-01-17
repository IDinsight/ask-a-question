"""Updated UserDB with workspaces. Add WorkspaceDB. Add user workspace association table.

Revision ID: c1d498545ec7
Revises: 27fd893400f8
Create Date: 2025-01-17 12:50:22.616398

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c1d498545ec7'
down_revision: Union[str, None] = '27fd893400f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('workspace',
    sa.Column('api_daily_quota', sa.Integer(), nullable=True),
    sa.Column('api_key_first_characters', sa.String(length=5), nullable=True),
    sa.Column('api_key_updated_datetime_utc', sa.DateTime(timezone=True), nullable=True),
    sa.Column('content_quota', sa.Integer(), nullable=True),
    sa.Column('created_datetime_utc', sa.DateTime(timezone=True), nullable=False),
    sa.Column('hashed_api_key', sa.String(length=96), nullable=True),
    sa.Column('updated_datetime_utc', sa.DateTime(timezone=True), nullable=False),
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('workspace_name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('workspace_id'),
    sa.UniqueConstraint('hashed_api_key'),
    sa.UniqueConstraint('workspace_name')
    )
    op.create_table('user_workspace_association',
    sa.Column('created_datetime_utc', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_datetime_utc', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('user_role', sa.Enum('ADMIN', 'READ_ONLY', name='userroles'), nullable=False),
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.user_id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspace.workspace_id'], ),
    sa.PrimaryKeyConstraint('user_id', 'workspace_id')
    )
    op.drop_constraint('user_hashed_api_key_key', 'user', type_='unique')
    op.drop_column('user', 'content_quota')
    op.drop_column('user', 'hashed_api_key')
    op.drop_column('user', 'api_key_updated_datetime_utc')
    op.drop_column('user', 'api_daily_quota')
    op.drop_column('user', 'api_key_first_characters')
    op.drop_column('user', 'is_admin')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('is_admin', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    op.add_column('user', sa.Column('api_key_first_characters', sa.VARCHAR(length=5), autoincrement=False, nullable=True))
    op.add_column('user', sa.Column('api_daily_quota', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('user', sa.Column('api_key_updated_datetime_utc', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.add_column('user', sa.Column('hashed_api_key', sa.VARCHAR(length=96), autoincrement=False, nullable=True))
    op.add_column('user', sa.Column('content_quota', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_unique_constraint('user_hashed_api_key_key', 'user', ['hashed_api_key'])
    op.drop_table('user_workspace_association')
    op.drop_table('workspace')
    # ### end Alembic commands ###
