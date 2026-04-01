"""drop is active from accounts

Revision ID: b1d2b4a7f9ce
Revises: 30f246f1a52a
Create Date: 2026-03-31 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1d2b4a7f9ce"
down_revision: str | None = "30f246f1a52a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("accounts", "is_active")


def downgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("accounts", "is_active", server_default=None)
