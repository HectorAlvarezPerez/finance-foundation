from enum import StrEnum


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_class]


class AccountType(StrEnum):
    CHECKING = "checking"
    SAVINGS = "savings"
    SHARED = "shared"
    OTHER = "other"


class CategoryType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
