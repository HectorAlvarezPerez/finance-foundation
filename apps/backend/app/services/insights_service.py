import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.insights import (
    InsightsAccountBalanceRead,
    InsightsMonthlyBucketRead,
    InsightsMonthlyRecapMonthRead,
    InsightsSummaryRead,
    InsightsTopCategoryRead,
)


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

    def get_summary(self, *, user_id: uuid.UUID) -> InsightsSummaryRead:
        snapshot = self.get_snapshot(user_id=user_id)
        accounts = snapshot.accounts
        categories = snapshot.categories
        transactions = snapshot.transactions

        category_map = {category.id: category for category in categories}
        account_map = {account.id: account for account in accounts}

        income = Decimal("0.00")
        expenses = Decimal("0.00")
        balance = Decimal("0.00")
        expense_by_category: defaultdict[uuid.UUID | None, Decimal] = defaultdict(
            lambda: Decimal("0.00")
        )
        balance_by_account: defaultdict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0.00"))
        monthly_buckets: dict[str, MonthlyBucket] = {}

        for transaction in transactions:
            amount = transaction.amount
            balance += amount

            if amount >= 0:
                income += amount
            else:
                expense_amount = abs(amount)
                expenses += expense_amount
                expense_by_category[transaction.category_id] += expense_amount

            balance_by_account[transaction.account_id] += amount

            month_key = transaction.date.strftime("%Y-%m")
            bucket = monthly_buckets.get(month_key)
            if bucket is None:
                bucket = MonthlyBucket(
                    month_key=month_key,
                    month_label=self.format_month_label(transaction.date),
                    income=Decimal("0.00"),
                    expenses=Decimal("0.00"),
                    net=Decimal("0.00"),
                    transactions=0,
                )
                monthly_buckets[month_key] = bucket

            if amount >= 0:
                bucket.income += amount
            else:
                bucket.expenses += abs(amount)
            bucket.net += amount
            bucket.transactions += 1

        top_categories = sorted(
            (
                self._build_top_category(category_map, category_id, total)
                for category_id, total in expense_by_category.items()
            ),
            key=lambda item: item.total,
            reverse=True,
        )[:6]

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

        return InsightsSummaryRead(
            income=income,
            expenses=expenses,
            balance=balance,
            transaction_count=len(transactions),
            top_categories=top_categories,
            monthly_comparison=monthly_comparison,
            account_balances=account_balances,
            available_recap_months=self.build_available_recap_months(transactions),
        )

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
