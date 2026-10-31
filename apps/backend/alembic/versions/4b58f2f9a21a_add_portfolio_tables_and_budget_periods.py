"""add portfolio tables and budget periods

Revision ID: 4b58f2f9a21a
Revises: 8f6c9a1d2b34
Create Date: 2026-04-25 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4b58f2f9a21a"
down_revision: str | None = "8f6c9a1d2b34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ACCOUNT_TYPE_VALUES = ("checking", "savings", "brokerage", "shared", "other")
ASSET_TYPE_VALUES = ("index_fund", "bond_fund", "crypto", "stock", "gold", "etf")
PRICE_SOURCE_VALUES = ("manual", "api")
TRADE_SIDE_VALUES = ("buy", "sell")
BUDGET_PERIOD_VALUES = ("monthly", "annual")


def _find_constraint_names(
    inspector: sa.Inspector,
    table_name: str,
    *,
    kind: str,
    predicate: callable,
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


def _sync_account_type_constraint(inspector: sa.Inspector) -> None:
    existing_names = _find_constraint_names(
        inspector,
        "accounts",
        kind="check",
        predicate=lambda constraint: "type" in (constraint.get("sqltext") or ""),
    )
    allowed = ", ".join(f"'{value}'" for value in ACCOUNT_TYPE_VALUES)
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("accounts", recreate="always") as batch_op:
            for name in existing_names:
                batch_op.drop_constraint(name, type_="check")
            batch_op.create_check_constraint(
                "account_type_allowed_values",
                f"type IN ({allowed})",
            )
        return

    for name in existing_names:
        _drop_constraint_raw("accounts", name)

    op.create_check_constraint(
        "account_type_allowed_values",
        "accounts",
        f"type IN ({allowed})",
    )


def _sync_budget_constraints(inspector: sa.Inspector) -> None:
    unique_names = _find_constraint_names(
        inspector,
        "budgets",
        kind="unique",
        predicate=lambda constraint: (
            set(constraint.get("column_names") or []) == {"user_id", "category_id", "year", "month"}
            or set(constraint.get("column_names") or [])
            == {"user_id", "category_id", "year", "period_type", "month"}
        ),
    )
    check_names = _find_constraint_names(
        inspector,
        "budgets",
        kind="check",
        predicate=lambda constraint: (
            "month" in (constraint.get("sqltext") or "")
            or "period_type" in (constraint.get("sqltext") or "")
        ),
    )
    budget_check_sql = (
        "("
        "(period_type = 'monthly' AND month IS NOT NULL AND month >= 1 AND month <= 12) "
        "OR "
        "(period_type = 'annual' AND month IS NULL)"
        ")"
    )
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("budgets", recreate="always") as batch_op:
            for name in unique_names:
                batch_op.drop_constraint(name, type_="unique")
            for name in check_names:
                batch_op.drop_constraint(name, type_="check")
            batch_op.create_check_constraint(
                "budget_period_month_range",
                budget_check_sql,
            )
            batch_op.create_unique_constraint(
                "user_category_year_period_month",
                ["user_id", "category_id", "year", "period_type", "month"],
            )
        return

    for name in unique_names:
        _drop_constraint_raw("budgets", name)
    for name in check_names:
        _drop_constraint_raw("budgets", name)

    op.create_check_constraint(
        "budget_period_month_range",
        "budgets",
        budget_check_sql,
    )
    op.create_unique_constraint(
        "user_category_year_period_month",
        "budgets",
        ["user_id", "category_id", "year", "period_type", "month"],
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    account_columns = {column["name"] for column in inspector.get_columns("accounts")}
    if "bank_name" in account_columns:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("accounts", recreate="always") as batch_op:
                batch_op.alter_column(
                    "type", existing_type=sa.String(length=8), type_=sa.String(length=16)
                )
        else:
            op.alter_column(
                "accounts", "type", existing_type=sa.String(length=8), type_=sa.String(length=16)
            )
        _sync_account_type_constraint(inspector)

    budget_columns = {column["name"] for column in inspector.get_columns("budgets")}
    if "period_type" not in budget_columns:
        op.add_column(
            "budgets",
            sa.Column(
                "period_type",
                sa.Enum(*BUDGET_PERIOD_VALUES, name="budget_period_type", native_enum=False),
                nullable=False,
                server_default="monthly",
            ),
        )

    op.execute("UPDATE budgets SET period_type = 'monthly' WHERE period_type IS NULL")
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("budgets", recreate="always") as batch_op:
            batch_op.alter_column(
                "period_type",
                existing_type=sa.Enum(
                    *BUDGET_PERIOD_VALUES, name="budget_period_type", native_enum=False
                ),
                server_default=None,
            )
            batch_op.alter_column("month", existing_type=sa.Integer(), nullable=True)
    else:
        op.alter_column("budgets", "period_type", server_default=None)
        op.alter_column("budgets", "month", existing_type=sa.Integer(), nullable=True)

    inspector = sa.inspect(bind)
    _sync_budget_constraints(inspector)

    existing_tables = set(inspector.get_table_names())
    if "holdings" not in existing_tables:
        op.create_table(
            "holdings",
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("asset_name", sa.String(length=255), nullable=False),
            sa.Column("asset_symbol", sa.String(length=32), nullable=True),
            sa.Column(
                "asset_type",
                sa.Enum(*ASSET_TYPE_VALUES, name="asset_type", native_enum=False),
                nullable=False,
            ),
            sa.Column("quantity", sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column("weekly_quantity", sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column("monthly_quantity", sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column("recurring_last_applied_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("average_buy_price", sa.Numeric(precision=15, scale=4), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
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
                name=op.f("fk_holdings_user_id_users"),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_holdings")),
        )
        op.create_index(op.f("ix_holdings_user_id"), "holdings", ["user_id"], unique=False)
        op.create_index(
            op.f("ix_holdings_asset_symbol"), "holdings", ["asset_symbol"], unique=False
        )

    if "prices" not in existing_tables:
        op.create_table(
            "prices",
            sa.Column("user_id", sa.Uuid(), nullable=True),
            sa.Column("asset_symbol", sa.String(length=64), nullable=False),
            sa.Column(
                "source",
                sa.Enum(*PRICE_SOURCE_VALUES, name="price_source", native_enum=False),
                nullable=False,
            ),
            sa.Column("price", sa.Numeric(precision=15, scale=4), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
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
                ["user_id"], ["users.id"], name=op.f("fk_prices_user_id_users"), ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_prices")),
        )
        op.create_index(op.f("ix_prices_user_id"), "prices", ["user_id"], unique=False)
        op.create_index(op.f("ix_prices_asset_symbol"), "prices", ["asset_symbol"], unique=False)
        op.create_index(op.f("ix_prices_as_of"), "prices", ["as_of"], unique=False)

    if "trades" not in existing_tables:
        op.create_table(
            "trades",
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("asset_symbol", sa.String(length=64), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column(
                "side",
                sa.Enum(*TRADE_SIDE_VALUES, name="trade_side", native_enum=False),
                nullable=False,
            ),
            sa.Column("quantity", sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column("price", sa.Numeric(precision=15, scale=4), nullable=False),
            sa.Column("fees", sa.Numeric(precision=15, scale=2), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("holding_id", sa.Uuid(), nullable=True),
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
                ["holding_id"],
                ["holdings.id"],
                name=op.f("fk_trades_holding_id_holdings"),
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"], ["users.id"], name=op.f("fk_trades_user_id_users"), ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_trades")),
        )
        op.create_index(op.f("ix_trades_user_id"), "trades", ["user_id"], unique=False)
        op.create_index(op.f("ix_trades_asset_symbol"), "trades", ["asset_symbol"], unique=False)
        op.create_index(op.f("ix_trades_date"), "trades", ["date"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "trades" in existing_tables:
        op.drop_index(op.f("ix_trades_date"), table_name="trades")
        op.drop_index(op.f("ix_trades_asset_symbol"), table_name="trades")
        op.drop_index(op.f("ix_trades_user_id"), table_name="trades")
        op.drop_table("trades")

    if "prices" in existing_tables:
        op.drop_index(op.f("ix_prices_as_of"), table_name="prices")
        op.drop_index(op.f("ix_prices_asset_symbol"), table_name="prices")
        op.drop_index(op.f("ix_prices_user_id"), table_name="prices")
        op.drop_table("prices")

    if "holdings" in existing_tables:
        op.drop_index(op.f("ix_holdings_asset_symbol"), table_name="holdings")
        op.drop_index(op.f("ix_holdings_user_id"), table_name="holdings")
        op.drop_table("holdings")

    budget_columns = {column["name"] for column in inspector.get_columns("budgets")}
    if "period_type" in budget_columns:
        op.execute("DELETE FROM budgets WHERE period_type = 'annual'")

        unique_names = _find_constraint_names(
            inspector,
            "budgets",
            kind="unique",
            predicate=lambda constraint: "period_type" in (constraint.get("column_names") or []),
        )
        for name in unique_names:
            _drop_constraint_raw("budgets", name)

        check_names = _find_constraint_names(
            inspector,
            "budgets",
            kind="check",
            predicate=lambda constraint: "period_type" in (constraint.get("sqltext") or ""),
        )
        for name in check_names:
            _drop_constraint_raw("budgets", name)

        op.alter_column("budgets", "month", existing_type=sa.Integer(), nullable=False)
        op.drop_column("budgets", "period_type")
        op.create_check_constraint(
            "ck_budgets_budget_month_range",
            "budgets",
            "month >= 1 AND month <= 12",
        )
        op.create_unique_constraint(
            "uq_budgets_user_category_year_month",
            "budgets",
            ["user_id", "category_id", "year", "month"],
        )

    account_columns = {column["name"] for column in inspector.get_columns("accounts")}
    if "bank_name" in account_columns:
        account_check_names = _find_constraint_names(
            inspector,
            "accounts",
            kind="check",
            predicate=lambda constraint: "type" in (constraint.get("sqltext") or ""),
        )
        for name in account_check_names:
            _drop_constraint_raw("accounts", name)

        op.create_check_constraint(
            "ck_accounts_account_type_allowed_values",
            "accounts",
            "type IN ('checking', 'savings', 'shared', 'other')",
        )
