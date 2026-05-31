"""add exchange_rates table

Revision ID: d4f5a6b78901
Revises: c3e4a7b89012
Create Date: 2026-05-30 21:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4f5a6b78901"
down_revision: str | None = "c3e4a7b89012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exchange_rates",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("from_currency", sa.String(length=3), nullable=False),
        sa.Column("to_currency", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(precision=20, scale=10), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_exchange_rates_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exchange_rates")),
        sa.UniqueConstraint(
            "user_id",
            "from_currency",
            "to_currency",
            "as_of",
            name="uq_exchange_rates_user_pair_as_of",
        ),
    )
    op.create_index(
        op.f("ix_exchange_rates_user_id"), "exchange_rates", ["user_id"], unique=False
    )
    op.create_index(op.f("ix_exchange_rates_as_of"), "exchange_rates", ["as_of"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_exchange_rates_as_of"), table_name="exchange_rates")
    op.drop_index(op.f("ix_exchange_rates_user_id"), table_name="exchange_rates")
    op.drop_table("exchange_rates")
