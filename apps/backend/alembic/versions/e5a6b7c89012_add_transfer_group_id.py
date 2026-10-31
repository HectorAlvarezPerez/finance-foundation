"""add transfer_group_id to transactions

Revision ID: e5a6b7c89012
Revises: d4f5a6b78901
Create Date: 2026-05-30 22:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5a6b7c89012"
down_revision: str | None = "d4f5a6b78901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("transfer_group_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_transactions_transfer_group_id"),
        "transactions",
        ["transfer_group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_transfer_group_id"), table_name="transactions")
    op.drop_column("transactions", "transfer_group_id")
