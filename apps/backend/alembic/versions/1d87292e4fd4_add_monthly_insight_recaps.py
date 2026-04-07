"""add monthly insight recaps

Revision ID: 1d87292e4fd4
Revises: b1d2b4a7f9ce
Create Date: 2026-04-06 22:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1d87292e4fd4"
down_revision: Union[str, Sequence[str], None] = "b1d2b4a7f9ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "monthly_insight_recaps",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("month_key", sa.String(length=7), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
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
            name=op.f("fk_monthly_insight_recaps_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monthly_insight_recaps")),
        sa.UniqueConstraint("user_id", "month_key", name="uq_monthly_insight_recaps_user_month"),
    )
    op.create_index(
        op.f("ix_monthly_insight_recaps_month_key"),
        "monthly_insight_recaps",
        ["month_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_monthly_insight_recaps_user_id"),
        "monthly_insight_recaps",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_monthly_insight_recaps_user_id"), table_name="monthly_insight_recaps")
    op.drop_index(
        op.f("ix_monthly_insight_recaps_month_key"),
        table_name="monthly_insight_recaps",
    )
    op.drop_table("monthly_insight_recaps")
