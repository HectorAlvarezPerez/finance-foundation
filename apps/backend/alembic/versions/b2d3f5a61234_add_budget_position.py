"""add position to budgets

Revision ID: b2d3f5a61234
Revises: a1c2e3f40987
Create Date: 2026-05-30 00:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2d3f5a61234"
down_revision: str | None = "a1c2e3f40987"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_budgets = sa.table(
    "budgets",
    sa.column("id", sa.Uuid()),
    sa.column("user_id", sa.Uuid()),
    sa.column("position", sa.Integer()),
    sa.column("created_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    op.add_column(
        "budgets",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.select(_budgets.c.id, _budgets.c.user_id, _budgets.c.created_at).order_by(
            _budgets.c.user_id, _budgets.c.created_at
        )
    ).all()

    position_by_user: dict[object, int] = {}
    for row in rows:
        position = position_by_user.get(row.user_id, 0)
        bind.execute(
            sa.update(_budgets).where(_budgets.c.id == row.id).values(position=position)
        )
        position_by_user[row.user_id] = position + 1

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("budgets") as batch_op:
            batch_op.alter_column("position", server_default=None)
    else:
        op.alter_column("budgets", "position", server_default=None)


def downgrade() -> None:
    op.drop_column("budgets", "position")
