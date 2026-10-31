"""make budgets recurring (drop year/month)

Revision ID: a1c2e3f40987
Revises: 4b58f2f9a21a
Create Date: 2026-05-30 00:00:00.000000

Budgets become recurring templates: a monthly budget applies to every month and
an annual budget to every year, so the concrete ``year``/``month`` columns are
removed. Existing concrete budgets are collapsed to one row per
``(user, category, period_type)`` keeping the most recent (highest year, then
month). This data step is destructive and cannot be reversed by downgrade.
"""

from collections.abc import Callable, Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c2e3f40987"
down_revision: str | None = "4b58f2f9a21a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_budgets = sa.table(
    "budgets",
    sa.column("id", sa.Uuid()),
    sa.column("user_id", sa.Uuid()),
    sa.column("category_id", sa.Uuid()),
    sa.column("period_type", sa.String()),
    sa.column("year", sa.Integer()),
    sa.column("month", sa.Integer()),
)


def _find_constraint_names(
    inspector: sa.Inspector,
    table_name: str,
    *,
    kind: str,
    predicate: Callable,
) -> list[str]:
    if kind == "check":
        constraints = inspector.get_check_constraints(table_name)
    elif kind == "unique":
        constraints = inspector.get_unique_constraints(table_name)
    else:
        return []

    matches: list[str] = []
    for constraint in constraints:
        if predicate(constraint):
            name = constraint.get("name")
            if name:
                matches.append(name)
    return matches


def _drop_constraint_raw(table_name: str, constraint_name: str) -> None:
    quoted_name = constraint_name.replace('"', '""')
    op.execute(sa.text(f'ALTER TABLE "{table_name}" DROP CONSTRAINT IF EXISTS "{quoted_name}"'))


def _collapse_duplicate_budgets(bind: sa.Connection) -> None:
    rows = bind.execute(
        sa.select(
            _budgets.c.id,
            _budgets.c.user_id,
            _budgets.c.category_id,
            _budgets.c.period_type,
            _budgets.c.year,
            _budgets.c.month,
        )
    ).all()

    keepers: dict[tuple[object, object, object], tuple[tuple[int, int], object]] = {}
    for row in rows:
        key = (row.user_id, row.category_id, row.period_type)
        rank = (row.year or 0, row.month or 0)
        current = keepers.get(key)
        if current is None or rank >= current[0]:
            keepers[key] = (rank, row.id)

    keep_ids = {keeper[1] for keeper in keepers.values()}
    delete_ids = [row.id for row in rows if row.id not in keep_ids]
    if delete_ids:
        bind.execute(sa.delete(_budgets).where(_budgets.c.id.in_(delete_ids)))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _collapse_duplicate_budgets(bind)

    unique_names = _find_constraint_names(
        inspector,
        "budgets",
        kind="unique",
        predicate=lambda constraint: bool(
            {"year", "month"} & set(constraint.get("column_names") or [])
        ),
    )
    check_names = _find_constraint_names(
        inspector,
        "budgets",
        kind="check",
        predicate=lambda constraint: "month" in (constraint.get("sqltext") or ""),
    )

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("budgets", recreate="always") as batch_op:
            for name in unique_names:
                batch_op.drop_constraint(name, type_="unique")
            for name in check_names:
                batch_op.drop_constraint(name, type_="check")
            batch_op.drop_column("month")
            batch_op.drop_column("year")
            batch_op.create_unique_constraint(
                "uq_budgets_user_category_period",
                ["user_id", "category_id", "period_type"],
            )
        return

    for name in unique_names:
        _drop_constraint_raw("budgets", name)
    for name in check_names:
        _drop_constraint_raw("budgets", name)

    op.drop_column("budgets", "month")
    op.drop_column("budgets", "year")
    op.create_unique_constraint(
        "uq_budgets_user_category_period",
        "budgets",
        ["user_id", "category_id", "period_type"],
    )


def downgrade() -> None:
    """Lossy: re-adds year/month with placeholder values (original data is gone)."""
    bind = op.get_bind()

    budget_check_sql = (
        "("
        "(period_type = 'monthly' AND month IS NOT NULL AND month >= 1 AND month <= 12) "
        "OR "
        "(period_type = 'annual' AND month IS NULL)"
        ")"
    )

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("budgets", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_budgets_user_category_period", type_="unique")
            batch_op.add_column(
                sa.Column("year", sa.Integer(), nullable=False, server_default="2026")
            )
            batch_op.add_column(sa.Column("month", sa.Integer(), nullable=True))
    else:
        _drop_constraint_raw("budgets", "uq_budgets_user_category_period")
        op.add_column(
            "budgets",
            sa.Column("year", sa.Integer(), nullable=False, server_default="2026"),
        )
        op.add_column("budgets", sa.Column("month", sa.Integer(), nullable=True))

    op.execute(
        sa.text("UPDATE budgets SET month = 1 WHERE period_type = 'monthly' AND month IS NULL")
    )

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("budgets") as batch_op:
            batch_op.alter_column("year", server_default=None)
            batch_op.create_check_constraint("budget_period_month_range", budget_check_sql)
            batch_op.create_unique_constraint(
                "uq_budgets_user_category_year_period_month",
                ["user_id", "category_id", "year", "period_type", "month"],
            )
        return

    op.alter_column("budgets", "year", server_default=None)
    op.create_check_constraint("budget_period_month_range", "budgets", budget_check_sql)
    op.create_unique_constraint(
        "uq_budgets_user_category_year_period_month",
        "budgets",
        ["user_id", "category_id", "year", "period_type", "month"],
    )
