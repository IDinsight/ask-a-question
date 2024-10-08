"""create content table

Revision ID: f269c75dbf69
Revises: 9eaf63e424ea
Create Date: 2024-02-18 19:38:36.817510

"""

from typing import Sequence, Union

import pgvector
import sqlalchemy as sa
from alembic import op
from app.config import (
    PGVECTOR_DISTANCE,
    PGVECTOR_EF_CONSTRUCTION,
    PGVECTOR_M,
    PGVECTOR_VECTOR_SIZE,
)

# revision identifiers, used by Alembic.
revision: str = "f269c75dbf69"
down_revision: Union[str, None] = "9eaf63e424ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.create_table(
        "content",
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column(
            "content_embedding",
            pgvector.sqlalchemy.Vector(dim=int(PGVECTOR_VECTOR_SIZE)),
            nullable=False,
        ),
        sa.Column("content_title", sa.String(length=150), nullable=False),
        sa.Column("content_text", sa.String(length=2000), nullable=False),
        sa.Column("content_language", sa.String(), nullable=False),
        sa.Column("content_metadata", sa.JSON(), nullable=False),
        sa.Column("created_datetime_utc", sa.DateTime(), nullable=False),
        sa.Column("updated_datetime_utc", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("content_id"),
    )
    op.execute(
        f"""CREATE INDEX content_idx ON content
        USING hnsw (content_embedding {PGVECTOR_DISTANCE})
        WITH (m = {PGVECTOR_M}, ef_construction = {PGVECTOR_EF_CONSTRUCTION})"""
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        "content_idx",
        table_name="content",
        postgresql_using="hnsw",
        postgresql_with={
            "M": {PGVECTOR_M},
            "ef_construction": {PGVECTOR_EF_CONSTRUCTION},
        },
        postgresql_ops={"embedding": {PGVECTOR_DISTANCE}},
    )
    op.drop_table("content")
    op.execute("DROP TYPE IF EXISTS identifiedlanguage;")
    op.execute("DROP EXTENSION IF EXISTS vector;")
    # ### end Alembic commands ###
