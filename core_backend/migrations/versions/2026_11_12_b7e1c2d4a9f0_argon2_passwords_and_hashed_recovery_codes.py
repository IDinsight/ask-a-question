"""Widen user.hashed_password for Argon2 and hash stored recovery codes.

Revision ID: b7e1c2d4a9f0
Revises: 3c54b4f5decf
Create Date: 2026-11-12 10:00:00.000000

1. `hashed_password` grows from VARCHAR(96) to VARCHAR(255). Argon2 hashes are ~97
   characters. Existing legacy SHA-256 hashes are left as they are; each one is
   replaced with an Argon2 hash the next time its user logs in.
2. Recovery codes were stored in plaintext. Each code that is not already a SHA-256
   hex digest is replaced with `sha256(code)`, which is what the app now stores and
   compares against. Users keep the same codes; only the stored form changes.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e1c2d4a9f0"
down_revision: Union[str, None] = "3c54b4f5decf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1.
    op.alter_column(
        "user",
        "hashed_password",
        existing_type=sa.String(length=96),
        type_=sa.String(length=255),
        existing_nullable=False,
    )

    # 2. Plaintext codes are 20 alphanumeric characters, so they can never match the
    # 64-hex pattern; already-hashed codes are left untouched (safe to re-run).
    # `sha256()` is built into PostgreSQL 11+.
    op.execute(
        """
        UPDATE "user"
        SET recovery_codes = ARRAY(
            SELECT CASE
                WHEN code ~ '^[0-9a-f]{64}$' THEN code
                ELSE encode(sha256(convert_to(code, 'UTF8')), 'hex')
            END
            FROM unnest(recovery_codes) AS code
        )
        WHERE recovery_codes IS NOT NULL
        """
    )


def downgrade() -> None:
    # 2. Hashing is one-way, so recovery codes stay hashed. Code from before this
    # revision compares plaintext, so after a downgrade users must be issued new codes.

    # 1. Fails if any Argon2 hash (>96 chars) exists, which is intended: shrinking
    # the column would truncate those hashes and lock the users out. Reset the
    # affected passwords first if a downgrade is really needed.
    op.alter_column(
        "user",
        "hashed_password",
        existing_type=sa.String(length=255),
        type_=sa.String(length=96),
        existing_nullable=False,
    )
