"""add auto categorization setting and remove refunds

Revision ID: 8f6c9a1d2b34
Revises: 5f0f4f9d0e21
Create Date: 2026-04-24 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f6c9a1d2b34"
down_revision: str | None = "5f0f4f9d0e21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    settings_columns = {column["name"] for column in inspector.get_columns("settings")}
    if "auto_categorization_enabled" not in settings_columns:
        op.add_column(
            "settings",
            sa.Column(
                "auto_categorization_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )

    transaction_columns = {column["name"] for column in inspector.get_columns("transactions")}
    if "is_refund" in transaction_columns:
        op.drop_column("transactions", "is_refund")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    transaction_columns = {column["name"] for column in inspector.get_columns("transactions")}
    if "is_refund" not in transaction_columns:
        op.add_column(
            "transactions",
            sa.Column("is_refund", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    settings_columns = {column["name"] for column in inspector.get_columns("settings")}
    if "auto_categorization_enabled" in settings_columns:
        op.drop_column("settings", "auto_categorization_enabled")
