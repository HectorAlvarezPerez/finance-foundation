"""add bank name to accounts

Revision ID: 30f246f1a52a
Revises: 36f049595730
Create Date: 2026-03-31 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "30f246f1a52a"
down_revision: str | None = "36f049595730"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("bank_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "bank_name")
