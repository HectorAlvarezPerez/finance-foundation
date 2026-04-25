from enum import StrEnum


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_class]


class AccountType(StrEnum):
    CHECKING = "checking"
    SAVINGS = "savings"
    BROKERAGE = "brokerage"
    SHARED = "shared"
    OTHER = "other"


class CategoryType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class BudgetPeriodType(StrEnum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class AssetType(StrEnum):
    INDEX_FUND = "index_fund"
    BOND_FUND = "bond_fund"
    CRYPTO = "crypto"
    STOCK = "stock"
    GOLD = "gold"
    ETF = "etf"


class PriceSource(StrEnum):
    MANUAL = "manual"
    API = "api"


class TradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"
