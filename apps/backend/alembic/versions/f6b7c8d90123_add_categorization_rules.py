"""add categorization_rules table

Revision ID: f6b7c8d90123
Revises: e5a6b7c89012
Create Date: 2026-05-31 20:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6b7c8d90123"
down_revision: str | None = "e5a6b7c89012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categorization_rules",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column(
            "match_type",
            sa.Enum("contains", "equals", "starts_with", name="rule_match_type", native_enum=False),
            nullable=False,
        ),
        sa.Column("pattern", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
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
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_categorization_rules_category_id_categories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_categorization_rules_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categorization_rules")),
    )
    op.create_index(
        op.f("ix_categorization_rules_user_id"),
        "categorization_rules",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_categorization_rules_category_id"),
        "categorization_rules",
        ["category_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_categorization_rules_category_id"), table_name="categorization_rules")
    op.drop_index(op.f("ix_categorization_rules_user_id"), table_name="categorization_rules")
    op.drop_table("categorization_rules")
