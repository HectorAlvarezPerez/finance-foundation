from __future__ import annotations

import argparse
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, or_, select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.holding import Holding
from app.models.price import Price
from app.models.settings import Settings
from app.models.trade import Trade
from app.models.transaction import Transaction
from app.models.user import User
from app.models.user_credential import UserCredential

COPY_BLOCK_PATTERN = re.compile(
    r'^COPY "public"\."(?P<table>[^"]+)" \((?P<columns>.*?)\) FROM stdin;$'
)
RECURRING_BUDGET_BASE_YEAR = 2000
UUID_NAMESPACE = uuid.UUID("37dfd0be-dca0-43a4-9634-fadca0d45184")


@dataclass(frozen=True)
class SelectedUser:
    source_user_id: uuid.UUID
    email: str
    password: str
    name: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import finance-tracker data into finance-foundation"
    )
    parser.add_argument("--dump-path", required=True, help="Path to the Supabase public data dump")
    parser.add_argument(
        "--user",
        dest="users",
        action="append",
        required=True,
        help="User mapping in the form source_uuid|email|password|optional name",
    )
    return parser.parse_args()


def parse_user_mapping(raw_value: str) -> SelectedUser:
    parts = [part.strip() for part in raw_value.split("|")]
    if len(parts) < 3:
        raise ValueError(f"Invalid --user mapping: {raw_value}")

    source_user_id = uuid.UUID(parts[0])
    email = parts[1].lower()
    password = parts[2]
    name = parts[3] if len(parts) > 3 and parts[3] else derive_name_from_email(email)
    return SelectedUser(source_user_id=source_user_id, email=email, password=password, name=name)


def derive_name_from_email(email: str) -> str:
    local_part = email.split("@", 1)[0]
    normalized = re.sub(r"[_\-.]+", " ", local_part)
    normalized = re.sub(r"\d+$", "", normalized).strip()
    if not normalized:
        normalized = local_part
    return " ".join(chunk.capitalize() for chunk in normalized.split())


def parse_dump(path: Path) -> dict[str, list[dict[str, str | None]]]:
    parsed: dict[str, list[dict[str, str | None]]] = {}
    current_table: str | None = None
    columns: list[str] = []
    rows: list[dict[str, str | None]] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if current_table is None:
            match = COPY_BLOCK_PATTERN.match(raw_line)
            if not match:
                continue
            current_table = match.group("table")
            columns = [column.strip().strip('"') for column in match.group("columns").split(", ")]
            rows = []
            continue

        if raw_line == r"\.":
            parsed[current_table] = rows
            current_table = None
            columns = []
            rows = []
            continue

        if not raw_line:
            continue

        raw_row = raw_line.split("\t")
        if len(raw_row) != len(columns):
            raise ValueError(
                f"Unexpected column count for table {current_table}: "
                f"expected {len(columns)}, got {len(raw_row)}"
            )
        row: dict[str, str | None] = {}
        for column, value in zip(columns, raw_row, strict=True):
            row[column] = None if value == r"\N" else value
        rows.append(row)

    if current_table is not None:
        raise ValueError(f"Unterminated COPY block for table {current_table}")

    return parsed


def parse_uuid(value: str | None) -> uuid.UUID | None:
    return uuid.UUID(value) if value else None


def parse_decimal(value: str | None) -> Decimal:
    if value is None:
        raise ValueError("Expected decimal value, received null")
    return Decimal(value)


def parse_datetime(value: str | None) -> datetime:
    if value is None:
        raise ValueError("Expected datetime value, received null")
    return datetime.fromisoformat(value)


def parse_date(value: str | None) -> date:
    if value is None:
        raise ValueError("Expected date value, received null")
    return date.fromisoformat(value)


def parse_updated_at(row: dict[str, str | None], *, fallback_key: str = "created_at") -> datetime:
    if row.get("updated_at"):
        return parse_datetime(row["updated_at"])
    return parse_datetime(row[fallback_key])


def filter_rows_for_users(
    rows: list[dict[str, str | None]],
    selected_users: dict[uuid.UUID, SelectedUser],
) -> list[dict[str, str | None]]:
    return [
        row
        for row in rows
        if parse_uuid(row.get("user_id")) in selected_users
    ]


def build_settings_row(
    source_rows: list[dict[str, str | None]],
    selected_user: SelectedUser,
    account_rows: list[dict[str, str | None]],
) -> Settings:
    source_row = next(
        (
            row
            for row in source_rows
            if parse_uuid(row.get("user_id")) == selected_user.source_user_id
        ),
        None,
    )
    default_currency = next(
        (row.get("currency") for row in account_rows if row.get("currency")),
        "EUR",
    )
    created_at = parse_datetime(source_row["created_at"]) if source_row else datetime.now(UTC)
    updated_at = parse_updated_at(source_row) if source_row else created_at
    source_default_currency = source_row.get("default_currency") if source_row else None
    source_locale = source_row.get("locale") if source_row else None
    source_theme = source_row.get("theme") if source_row else None

    return Settings(
        user_id=selected_user.source_user_id,
        default_currency=source_default_currency or default_currency or "EUR",
        locale=source_locale or "es",
        theme=source_theme or "system",
        auto_categorization_enabled=True,
        created_at=created_at,
        updated_at=updated_at,
    )


def build_budget_rows(
    source_rows: Iterable[dict[str, str | None]],
    *,
    selected_users: dict[uuid.UUID, SelectedUser],
    current_year: int,
) -> list[Budget]:
    budgets: list[Budget] = []

    for row in source_rows:
        source_user_id = parse_uuid(row.get("user_id"))
        if source_user_id not in selected_users:
            continue

        period_type = row["period_type"] or "monthly"
        original_year = int(row["year"] or current_year)
        amount = parse_decimal(row["amount"])
        currency = row["currency"] or "EUR"
        created_at = parse_datetime(row["created_at"])
        updated_at = parse_datetime(row["updated_at"]) if row.get("updated_at") else created_at

        if period_type == "monthly" and original_year == RECURRING_BUDGET_BASE_YEAR:
            for month in range(1, 13):
                budgets.append(
                    Budget(
                        id=uuid.uuid5(
                            UUID_NAMESPACE,
                            f"{row['id']}:monthly:{current_year}:{month}",
                        ),
                        user_id=source_user_id,
                        category_id=parse_uuid(row["category_id"]),
                        year=current_year,
                        period_type="monthly",
                        month=month,
                        currency=currency,
                        amount=amount,
                        created_at=created_at,
                        updated_at=updated_at,
                    )
                )
            continue

        target_year = current_year if original_year == RECURRING_BUDGET_BASE_YEAR else original_year
        month_value = row.get("month")
        budgets.append(
            Budget(
                id=parse_uuid(row["id"]),
                user_id=source_user_id,
                category_id=parse_uuid(row["category_id"]),
                year=target_year,
                period_type=period_type,
                month=int(month_value) if month_value else None,
                currency=currency,
                amount=amount,
                created_at=created_at,
                updated_at=updated_at,
            )
        )

    return budgets


def main() -> None:
    args = parse_args()
    selected_users = {
        user.source_user_id: user
        for user in (parse_user_mapping(raw_value) for raw_value in args.users)
    }
    dump = parse_dump(Path(args.dump_path))
    current_year = datetime.now(UTC).year

    with SessionLocal() as session:
        existing_users = session.scalars(
            select(User).where(
                or_(
                    User.email.in_([user.email for user in selected_users.values()]),
                    User.id.in_(list(selected_users.keys())),
                )
            )
        ).all()
        if existing_users:
            session.execute(delete(User).where(User.id.in_([user.id for user in existing_users])))
            session.flush()

        users = [
            User(
                id=user.source_user_id,
                auth_provider_user_id=f"local-migrated:{user.source_user_id}",
                email=user.email,
                name=user.name,
            )
            for user in selected_users.values()
        ]
        session.add_all(users)
        session.flush()

        session.add_all(
            [
                UserCredential(
                    user_id=user.source_user_id,
                    password_hash=hash_password(user.password),
                )
                for user in selected_users.values()
            ]
        )

        source_accounts = filter_rows_for_users(dump.get("accounts", []), selected_users)
        source_categories = filter_rows_for_users(dump.get("categories", []), selected_users)
        source_transactions = filter_rows_for_users(dump.get("transactions", []), selected_users)
        source_holdings = filter_rows_for_users(dump.get("holdings", []), selected_users)
        source_prices = filter_rows_for_users(dump.get("prices", []), selected_users)
        source_trades = filter_rows_for_users(dump.get("trades", []), selected_users)

        session.add_all(
            [
                build_settings_row(
                    dump.get("settings", []),
                    user,
                    [
                        row
                        for row in source_accounts
                        if parse_uuid(row.get("user_id")) == user.source_user_id
                    ],
                )
                for user in selected_users.values()
            ]
        )

        session.add_all(
            [
                Account(
                    id=parse_uuid(row["id"]),
                    user_id=parse_uuid(row["user_id"]),
                    name=row["name"] or "Cuenta",
                    bank_name=None,
                    type=row["type"] or "other",
                    currency=row["currency"] or "EUR",
                    color=None,
                    icon=None,
                    created_at=parse_datetime(row["created_at"]),
                    updated_at=parse_updated_at(row),
                )
                for row in source_accounts
            ]
        )

        session.add_all(
            [
                Category(
                    id=parse_uuid(row["id"]),
                    user_id=parse_uuid(row["user_id"]),
                    name=row["name"] or "Categoría",
                    type=row["type"] or "expense",
                    color=row.get("color"),
                    icon=row.get("icon"),
                    created_at=parse_datetime(row["created_at"]),
                    updated_at=parse_datetime(row["created_at"]),
                )
                for row in source_categories
            ]
        )

        session.add_all(
            [
                Transaction(
                    id=parse_uuid(row["id"]),
                    user_id=parse_uuid(row["user_id"]),
                    account_id=parse_uuid(row["account_id"]),
                    category_id=parse_uuid(row["category_id"]),
                    date=parse_date(row["date"]),
                    amount=parse_decimal(row["amount"]),
                    currency=row["currency"] or "EUR",
                    description=row["description"] or "Movimiento",
                    notes=row.get("notes"),
                    created_at=parse_datetime(row["created_at"]),
                    updated_at=parse_updated_at(row),
                )
                for row in source_transactions
            ]
        )

        session.add_all(
            build_budget_rows(
                dump.get("budgets", []),
                selected_users=selected_users,
                current_year=current_year,
            )
        )

        session.add_all(
            [
                Holding(
                    id=parse_uuid(row["id"]),
                    user_id=parse_uuid(row["user_id"]),
                    asset_name=row["asset_name"] or "Asset",
                    asset_symbol=row.get("asset_symbol"),
                    asset_type=row["asset_type"] or "stock",
                    quantity=parse_decimal(row["quantity"]),
                    weekly_quantity=parse_decimal(row["weekly_quantity"]),
                    monthly_quantity=parse_decimal(row["monthly_quantity"]),
                    recurring_last_applied_at=parse_datetime(row["recurring_last_applied_at"]),
                    average_buy_price=parse_decimal(row["average_buy_price"]),
                    currency=row["currency"] or "EUR",
                    created_at=parse_datetime(row["created_at"]),
                    updated_at=parse_updated_at(row),
                )
                for row in source_holdings
            ]
        )

        session.add_all(
            [
                Price(
                    id=parse_uuid(row["id"]),
                    user_id=parse_uuid(row["user_id"]),
                    asset_symbol=row["asset_symbol"] or "UNKNOWN",
                    source=row["source"] or "manual",
                    price=parse_decimal(row["price"]),
                    currency=row["currency"] or "EUR",
                    as_of=parse_datetime(row["as_of"]),
                    created_at=parse_datetime(row["created_at"]),
                    updated_at=parse_datetime(row["created_at"]),
                )
                for row in source_prices
            ]
        )

        session.add_all(
            [
                Trade(
                    id=parse_uuid(row["id"]),
                    user_id=parse_uuid(row["user_id"]),
                    asset_symbol=row["asset_symbol"] or "UNKNOWN",
                    date=parse_date(row["date"]),
                    side=row["side"] or "buy",
                    quantity=parse_decimal(row["quantity"]),
                    price=parse_decimal(row["price"]),
                    fees=parse_decimal(row["fees"]),
                    currency=row["currency"] or "EUR",
                    holding_id=parse_uuid(row["holding_id"]),
                    created_at=parse_datetime(row["created_at"]),
                    updated_at=parse_updated_at(row),
                )
                for row in source_trades
            ]
        )

        session.commit()

        migrated_accounts = len(source_accounts)
        migrated_categories = len(source_categories)
        migrated_transactions = len(source_transactions)
        migrated_holdings = len(source_holdings)
        migrated_prices = len(source_prices)
        migrated_trades = len(source_trades)
        migrated_budgets = len(
            build_budget_rows(
                dump.get("budgets", []),
                selected_users=selected_users,
                current_year=current_year,
            )
        )

    print("Imported users:", len(selected_users))
    print("Imported accounts:", migrated_accounts)
    print("Imported categories:", migrated_categories)
    print("Imported transactions:", migrated_transactions)
    print("Imported budgets:", migrated_budgets)
    print("Imported holdings:", migrated_holdings)
    print("Imported prices:", migrated_prices)
    print("Imported trades:", migrated_trades)


if __name__ == "__main__":
    main()
