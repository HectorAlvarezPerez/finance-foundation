"""add is_refund to transactions

Revision ID: 5f0f4f9d0e21
Revises: eed3782eb47d
Create Date: 2026-04-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5f0f4f9d0e21"
down_revision: str | None = "eed3782eb47d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("transactions")}
    if "is_refund" not in columns:
        op.add_column(
            "transactions",
            sa.Column("is_refund", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("transactions")}
    if "is_refund" in columns:
        op.drop_column("transactions", "is_refund")
