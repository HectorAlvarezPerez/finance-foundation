"""add unique constraint to prices

Revision ID: c3e4a7b89012
Revises: b2d3f5a61234
Create Date: 2026-05-30 00:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3e4a7b89012"
down_revision: str | None = "b2d3f5a61234"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "uq_prices_user_symbol_source_as_of"

_prices = sa.table(
    "prices",
    sa.column("id", sa.Uuid()),
    sa.column("user_id", sa.Uuid()),
    sa.column("asset_symbol", sa.String()),
    sa.column("source", sa.String()),
    sa.column("as_of", sa.DateTime(timezone=True)),
    sa.column("created_at", sa.DateTime(timezone=True)),
)


def _dedupe(bind: sa.Connection) -> None:
    rows = bind.execute(
        sa.select(
            _prices.c.id,
            _prices.c.user_id,
            _prices.c.asset_symbol,
            _prices.c.source,
            _prices.c.as_of,
            _prices.c.created_at,
        )
    ).all()

    keepers: dict[tuple[object, object, object, object], tuple[object, object]] = {}
    delete_ids: list[object] = []
    for row in rows:
        key = (row.user_id, row.asset_symbol, row.source, row.as_of)
        current = keepers.get(key)
        rank = row.created_at
        if current is None or (rank is not None and rank >= current[0]):
            if current is not None:
                delete_ids.append(current[1])
            keepers[key] = (rank, row.id)
        else:
            delete_ids.append(row.id)

    if delete_ids:
        bind.execute(sa.delete(_prices).where(_prices.c.id.in_(delete_ids)))


def upgrade() -> None:
    bind = op.get_bind()
    _dedupe(bind)

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("prices") as batch_op:
            batch_op.create_unique_constraint(
                CONSTRAINT_NAME,
                ["user_id", "asset_symbol", "source", "as_of"],
            )
        return

    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "prices",
        ["user_id", "asset_symbol", "source", "as_of"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("prices") as batch_op:
            batch_op.drop_constraint(CONSTRAINT_NAME, type_="unique")
        return

    op.drop_constraint(CONSTRAINT_NAME, "prices", type_="unique")
