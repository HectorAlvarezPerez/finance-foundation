import re
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models.account import Account
from app.models.category import Category
from app.models.enums import CategoryType
from app.models.transaction import Transaction
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.insights import (
    InsightsAccountBalanceRead,
    InsightsCategoryTotalRead,
    InsightsDailyPacingRead,
    InsightsMonthlyBucketRead,
    InsightsMonthlyRecapMonthRead,
    InsightsSummaryRead,
    InsightsTopCategoryRead,
    NetWorthPointRead,
    SubscriptionRead,
)
from app.services.fx_service import CurrencyConverter


@dataclass
class MonthlyBucket:
    month_key: str
    month_label: str
    income: Decimal
    expenses: Decimal
    net: Decimal
    transactions: int


@dataclass
class InsightsDataSnapshot:
    accounts: list[Account]
    categories: list[Category]
    transactions: list[Transaction]


class InsightsService:
    def __init__(
        self,
        account_repository: AccountRepository,
        category_repository: CategoryRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        self.account_repository = account_repository
        self.category_repository = category_repository
        self.transaction_repository = transaction_repository

    def get_snapshot(self, *, user_id: uuid.UUID) -> InsightsDataSnapshot:
        return InsightsDataSnapshot(
            accounts=self.account_repository.list_all_for_user(
                user_id=user_id,
                sort_by="name",
                sort_order="asc",
            ),
            categories=self.category_repository.list_all_for_user(
                user_id=user_id,
                sort_by="name",
                sort_order="asc",
            ),
            transactions=self.transaction_repository.list_all_for_user(
                user_id=user_id,
                sort_by="date",
                sort_order="desc",
            ),
        )

    def get_summary(
        self,
        *,
        user_id: uuid.UUID,
        base_currency: str | None = None,
        converter: "CurrencyConverter | None" = None,
        month_key: str | None = None,
    ) -> InsightsSummaryRead:
        """Aggregate insights for the user.

        When ``month_key`` (``YYYY-MM``) is provided, the cash-flow fields
        (income, expenses, transaction_count, top/expense categories, daily
        pacing, savings_rate) are scoped to that month. Balance, account
        balances, monthly comparison and available recap months stay global.
        """
        snapshot = self.get_snapshot(user_id=user_id)
        accounts = snapshot.accounts
        categories = snapshot.categories
        transactions = snapshot.transactions

        category_map = {category.id: category for category in categories}
        account_map = {account.id: account for account in accounts}

        def to_base(amount: Decimal, currency: str) -> Decimal:
            # Convert cash-flow figures to the user's base currency. When no rate
            # exists (or FX is not configured) fall back to the raw amount.
            if base_currency is None or converter is None:
                return amount
            converted = converter.convert(amount, currency, base_currency)
            return converted.quantize(Decimal("0.01")) if converted is not None else amount

        income = Decimal("0.00")
        expenses = Decimal("0.00")
        balance = Decimal("0.00")
        transaction_count = 0
        expense_by_category: defaultdict[uuid.UUID | None, Decimal] = defaultdict(
            lambda: Decimal("0.00")
        )
        balance_by_account: defaultdict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0.00"))
        monthly_buckets: dict[str, MonthlyBucket] = {}

        for transaction in transactions:
            # Account balances stay in each account's own currency; cash-flow
            # totals are normalised to the base currency.
            amount = to_base(transaction.amount, transaction.currency)
            balance += amount
            balance_by_account[transaction.account_id] += transaction.amount

            category = (
                category_map.get(transaction.category_id)
                if transaction.category_id is not None
                else None
            )
            is_transfer = transaction.transfer_group_id is not None or (
                category is not None and category.type == CategoryType.TRANSFER
            )

            transaction_month_key = transaction.date.strftime("%Y-%m")
            # Cash-flow scope: everything when unscoped, one month otherwise.
            in_scope = month_key is None or transaction_month_key == month_key
            if in_scope:
                transaction_count += 1

            bucket = monthly_buckets.get(transaction_month_key)
            if bucket is None:
                bucket = MonthlyBucket(
                    month_key=transaction_month_key,
                    month_label=self.format_month_label(transaction.date),
                    income=Decimal("0.00"),
                    expenses=Decimal("0.00"),
                    net=Decimal("0.00"),
                    transactions=0,
                )
                monthly_buckets[transaction_month_key] = bucket
            bucket.transactions += 1

            # Transfers move money between the user's own accounts: they still
            # affect account balances, but they are not income or expenses and
            # must not leak into cash-flow totals (ingresos vs gastos).
            if is_transfer:
                continue

            category_type = category.type if category is not None else None
            if category_type == CategoryType.INCOME:
                if in_scope:
                    income += amount
                bucket.income += amount
                bucket.net += amount
            elif category_type == CategoryType.EXPENSE:
                expense_amount = abs(amount)
                if in_scope:
                    expenses += expense_amount
                    expense_by_category[transaction.category_id] += expense_amount
                bucket.expenses += expense_amount
                bucket.net += amount

        top_categories = sorted(
            (
                self._build_top_category(category_map, category_id, total)
                for category_id, total in expense_by_category.items()
            ),
            key=lambda item: item.total,
            reverse=True,
        )[:6]

        expense_categories = sorted(
            (
                self._build_category_total(category_map, category_id, total)
                for category_id, total in expense_by_category.items()
            ),
            key=lambda item: item.total,
            reverse=True,
        )

        monthly_comparison = [
            InsightsMonthlyBucketRead(
                month_key=bucket.month_key,
                month_label=bucket.month_label,
                income=bucket.income,
                expenses=bucket.expenses,
                net=bucket.net,
                transactions=bucket.transactions,
            )
            for _, bucket in sorted(monthly_buckets.items())
        ][-6:]

        account_balances = sorted(
            (
                self._build_account_balance(account_map, account_id, total)
                for account_id, total in balance_by_account.items()
            ),
            key=lambda item: abs(item.total),
            reverse=True,
        )

        today = date.today()
        real_current_month_key = today.strftime("%Y-%m")
        # Pacing compares the selected month (or the real current month when
        # unscoped) against the immediately previous calendar month.
        selected_month_key = month_key if month_key is not None else real_current_month_key
        selected_year = int(selected_month_key[:4])
        selected_month = int(selected_month_key[5:7])
        if selected_month == 1:
            prev_year = selected_year - 1
            prev_month = 12
        else:
            prev_year = selected_year
            prev_month = selected_month - 1
        prev_month_key = f"{prev_year}-{prev_month:02d}"

        # Only the real, in-progress calendar month gets truncated after today;
        # past months show their full series.
        truncate_after_day = today.day if selected_month_key == real_current_month_key else None

        current_pacing = {day: Decimal("0.00") for day in range(1, 32)}
        prev_pacing = {day: Decimal("0.00") for day in range(1, 32)}

        for t in transactions:
            if t.transfer_group_id is not None:
                continue
            category = category_map.get(t.category_id) if t.category_id is not None else None
            if category is None or category.type != CategoryType.EXPENSE:
                continue
            spent = abs(to_base(t.amount, t.currency))
            pacing_month_key = t.date.strftime("%Y-%m")
            if pacing_month_key == selected_month_key:
                current_pacing[t.date.day] += spent
            elif pacing_month_key == prev_month_key:
                prev_pacing[t.date.day] += spent

        current_cum = Decimal("0.00")
        prev_cum = Decimal("0.00")
        daily_pacing = []
        for day in range(1, 32):
            current_cum += current_pacing[day]
            prev_cum += prev_pacing[day]

            curr_val = (
                current_cum if truncate_after_day is None or day <= truncate_after_day else None
            )
            daily_pacing.append(
                InsightsDailyPacingRead(
                    day=day,
                    current_month_cumulative=curr_val,
                    previous_month_cumulative=prev_cum,
                )
            )

        savings_rate = 0.0
        if income > 0:
            savings_rate = max(0.0, float(((income - expenses) / income) * 100))

        return InsightsSummaryRead(
            income=income,
            expenses=expenses,
            balance=balance,
            transaction_count=transaction_count,
            top_categories=top_categories,
            monthly_comparison=monthly_comparison,
            account_balances=account_balances,
            available_recap_months=self.build_available_recap_months(transactions),
            expense_categories=expense_categories,
            daily_pacing=daily_pacing,
            savings_rate=round(savings_rate, 2),
        )

    def get_net_worth_history(
        self,
        *,
        user_id: uuid.UUID,
        base_currency: str | None = None,
        converter: "CurrencyConverter | None" = None,
        months: int = 12,
    ) -> tuple[Decimal, list[NetWorthPointRead]]:
        """Cumulative cash balance (all accounts) at each month-end, in base currency.

        Returns (current_accounts_value, monthly_history). Investment value is not
        reconstructable without price history, so it is added by the caller for the
        current figure only.
        """
        transactions = self.transaction_repository.list_all_for_user(
            user_id=user_id,
            sort_by="date",
            sort_order="asc",
        )

        def to_base(amount: Decimal, currency: str) -> Decimal:
            if base_currency is None or converter is None:
                return amount
            converted = converter.convert(amount, currency, base_currency)
            return converted.quantize(Decimal("0.01")) if converted is not None else amount

        running = Decimal("0.00")
        month_end: dict[str, Decimal] = {}
        for transaction in transactions:
            running += to_base(transaction.amount, transaction.currency)
            month_end[transaction.date.strftime("%Y-%m")] = running

        history = [
            NetWorthPointRead(
                month_key=month_key,
                month_label=self.format_month_label_parts(
                    int(month_key[:4]), int(month_key[5:7])
                ),
                value=value,
            )
            for month_key, value in sorted(month_end.items())
        ][-months:]

        return running, history

    @staticmethod
    def _subscription_key(description: str) -> str:
        text = (description or "").lower()
        text = re.sub(r"[0-9]+", " ", text)
        text = re.sub(r"[^0-9a-záéíóúñü ]", " ", text)
        tokens = [token for token in text.split() if len(token) > 2][:3]
        return " ".join(tokens)

    def detect_subscriptions(
        self,
        *,
        user_id: uuid.UUID,
        base_currency: str | None = None,
        converter: "CurrencyConverter | None" = None,
    ) -> tuple[list[SubscriptionRead], Decimal]:
        """Detect likely subscriptions: recurring same-merchant expenses with a
        stable amount across at least 3 distinct months."""
        snapshot = self.get_snapshot(user_id=user_id)
        category_map = {category.id: category for category in snapshot.categories}

        groups: defaultdict[tuple[str, str], list[Transaction]] = defaultdict(list)
        for transaction in snapshot.transactions:
            if transaction.amount >= 0 or transaction.transfer_group_id is not None:
                continue
            category = (
                category_map.get(transaction.category_id) if transaction.category_id else None
            )
            if category is not None and category.type == CategoryType.TRANSFER:
                continue
            key = self._subscription_key(transaction.description)
            if not key:
                continue
            groups[(key, transaction.currency)].append(transaction)

        items: list[SubscriptionRead] = []
        for (_, currency), txns in groups.items():
            if len(txns) < 3:
                continue
            if len({t.date.strftime("%Y-%m") for t in txns}) < 3:
                continue
            amounts = [abs(t.amount) for t in txns]
            mean = sum(amounts, Decimal("0")) / len(amounts)
            if mean <= 0 or (max(amounts) - min(amounts)) / mean > Decimal("0.35"):
                continue

            label = Counter(t.description for t in txns).most_common(1)[0][0]
            category_id = Counter(t.category_id for t in txns).most_common(1)[0][0]
            category = category_map.get(category_id) if category_id else None
            items.append(
                SubscriptionRead(
                    label=label,
                    category_id=category_id,
                    category_name=category.name if category is not None else None,
                    currency=currency,
                    monthly_estimate=mean.quantize(Decimal("0.01")),
                    occurrences=len(txns),
                    last_date=max(t.date for t in txns),
                )
            )

        items.sort(key=lambda item: item.monthly_estimate, reverse=True)

        total = Decimal("0.00")
        for item in items:
            if base_currency is not None and converter is not None:
                converted = converter.convert(item.monthly_estimate, item.currency, base_currency)
                total += (
                    converted.quantize(Decimal("0.01"))
                    if converted is not None
                    else item.monthly_estimate
                )
            else:
                total += item.monthly_estimate

        return items, total

    def build_available_recap_months(
        self,
        transactions: list[Transaction],
    ) -> list[InsightsMonthlyRecapMonthRead]:
        month_keys = {transaction.date.strftime("%Y-%m") for transaction in transactions}
        return [
            InsightsMonthlyRecapMonthRead(
                month_key=month_key,
                month_label=self.format_month_label_parts(int(month_key[:4]), int(month_key[5:7])),
            )
            for month_key in sorted(month_keys, reverse=True)
        ]

    def format_month_label(self, value: date) -> str:
        return self.format_month_label_parts(value.year, value.month)

    def format_month_label_parts(self, year: int, month: int) -> str:
        month_labels = {
            1: "ene",
            2: "feb",
            3: "mar",
            4: "abr",
            5: "may",
            6: "jun",
            7: "jul",
            8: "ago",
            9: "sept",
            10: "oct",
            11: "nov",
            12: "dic",
        }
        return f"{month_labels[month]} {str(year)[-2:]}"

    def _build_top_category(
        self,
        category_map: dict[uuid.UUID, Category],
        category_id: uuid.UUID | None,
        total: Decimal,
    ) -> InsightsTopCategoryRead:
        category = category_map.get(category_id) if category_id is not None else None
        name = category.name if category is not None else "Sin categoría"
        color = category.color if category is not None and category.color else "#94a3b8"
        return InsightsTopCategoryRead(
            category_id=category_id,
            name=name,
            color=color,
            total=total,
        )

    def _build_category_total(
        self,
        category_map: dict[uuid.UUID, Category],
        category_id: uuid.UUID | None,
        total: Decimal,
    ) -> InsightsCategoryTotalRead:
        category = category_map.get(category_id) if category_id is not None else None
        name = category.name if category is not None else "Sin categoría"
        color = category.color if category is not None and category.color else "#94a3b8"
        ctype = category.type.value if category is not None else "expense"
        return InsightsCategoryTotalRead(
            category_id=category_id,
            name=name,
            color=color,
            type=ctype,
            total=total,
        )

    def _build_account_balance(
        self,
        account_map: dict[uuid.UUID, Account],
        account_id: uuid.UUID,
        total: Decimal,
    ) -> InsightsAccountBalanceRead:
        account = account_map.get(account_id)
        return InsightsAccountBalanceRead(
            account_id=account_id,
            name=account.name if account is not None else "Cuenta",
            currency=account.currency if account is not None else "EUR",
            total=total,
        )
