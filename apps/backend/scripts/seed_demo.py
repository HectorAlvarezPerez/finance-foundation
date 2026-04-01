from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import AccountType, CategoryType
from app.models.settings import Settings
from app.models.transaction import Transaction
from app.models.user import User
from app.models.user_credential import UserCredential

DEMO_EMAIL = "demo@finance-foundation.app"
DEMO_PASSWORD = "Demo12345"
DEMO_NAME = "Demo User"


def add_months(base_date: date, offset: int) -> date:
    month_index = base_date.month - 1 + offset
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base_date.day, monthrange(year, month)[1])
    return date(year, month, day)


def seed_demo_data() -> None:
    today = date.today()

    with SessionLocal() as session:
        existing_user = session.scalar(select(User).where(User.email == DEMO_EMAIL))
        if existing_user is not None:
            session.delete(existing_user)
            session.commit()

        user = User(
            auth_provider_user_id="local:demo-user",
            email=DEMO_EMAIL,
            name=DEMO_NAME,
        )
        session.add(user)
        session.flush()

        credential = UserCredential(
            user_id=user.id,
            password_hash=hash_password(DEMO_PASSWORD),
        )
        session.add(credential)

        settings = Settings(
            user_id=user.id,
            default_currency="EUR",
            locale="es-ES",
            theme="system",
        )
        session.add(settings)

        main_account = Account(
            user_id=user.id,
            name="Cuenta principal",
            bank_name="Santander",
            type=AccountType.CHECKING,
            currency="EUR",
        )
        savings_account = Account(
            user_id=user.id,
            name="Ahorro",
            bank_name="Openbank",
            type=AccountType.SAVINGS,
            currency="EUR",
        )
        shared_account = Account(
            user_id=user.id,
            name="Compartida",
            bank_name="BBVA",
            type=AccountType.SHARED,
            currency="EUR",
        )
        session.add_all([main_account, savings_account, shared_account])
        session.flush()

        salary_category = Category(
            user_id=user.id,
            name="Nómina",
            type=CategoryType.INCOME,
            color="#16a34a",
            icon="wallet",
        )
        food_category = Category(
            user_id=user.id,
            name="Comida",
            type=CategoryType.EXPENSE,
            color="#2563eb",
            icon="utensils",
        )
        housing_category = Category(
            user_id=user.id,
            name="Vivienda",
            type=CategoryType.EXPENSE,
            color="#7c3aed",
            icon="house",
        )
        transport_category = Category(
            user_id=user.id,
            name="Transporte",
            type=CategoryType.EXPENSE,
            color="#ea580c",
            icon="car",
        )
        leisure_category = Category(
            user_id=user.id,
            name="Ocio",
            type=CategoryType.EXPENSE,
            color="#db2777",
            icon="gamepad-2",
        )
        transfer_category = Category(
            user_id=user.id,
            name="Transferencia",
            type=CategoryType.TRANSFER,
            color="#64748b",
            icon="arrow-right-left",
        )
        session.add_all(
            [
                salary_category,
                food_category,
                housing_category,
                transport_category,
                leisure_category,
                transfer_category,
            ]
        )
        session.flush()

        monthly_templates = [
            (
                1,
                main_account.id,
                salary_category.id,
                Decimal("2450.00"),
                "Nómina mensual",
                "Ingreso principal del mes",
            ),
            (
                2,
                main_account.id,
                housing_category.id,
                Decimal("-950.00"),
                "Alquiler",
                "Pago recurrente mensual",
            ),
            (
                3,
                main_account.id,
                transport_category.id,
                Decimal("-18.50"),
                "Abono transporte",
                "Recarga mensual",
            ),
            (
                4,
                main_account.id,
                food_category.id,
                Decimal("-62.30"),
                "Compra semanal",
                "Supermercado",
            ),
            (
                5,
                main_account.id,
                food_category.id,
                Decimal("-9.80"),
                "Café y desayuno",
                "Antes de entrar a la oficina",
            ),
            (
                6,
                shared_account.id,
                leisure_category.id,
                Decimal("-24.00"),
                "Cine",
                "Plan viernes",
            ),
            (
                8,
                main_account.id,
                food_category.id,
                Decimal("-41.20"),
                "Mercado del barrio",
                "Fruta y verdura",
            ),
            (
                9,
                main_account.id,
                transfer_category.id,
                Decimal("-350.00"),
                "Transferencia a ahorro",
                "Aportación automática al colchón",
            ),
            (
                9,
                savings_account.id,
                transfer_category.id,
                Decimal("350.00"),
                "Transferencia desde cuenta principal",
                "Movimiento espejo a ahorro",
            ),
            (
                11,
                main_account.id,
                transport_category.id,
                Decimal("-12.40"),
                "Taxi al aeropuerto",
                "Llegaba justo a una reunión",
            ),
            (
                12,
                main_account.id,
                food_category.id,
                Decimal("-28.75"),
                "Glovo",
                "Cena rápida en casa",
            ),
            (
                13,
                shared_account.id,
                leisure_category.id,
                Decimal("-46.00"),
                "Cena con amigos",
                "Cuenta compartida",
            ),
            (
                15,
                main_account.id,
                food_category.id,
                Decimal("-57.60"),
                "Compra semanal",
                "Supermercado",
            ),
            (
                16,
                shared_account.id,
                housing_category.id,
                Decimal("-64.50"),
                "Internet y streaming",
                "Gastos del piso compartido",
            ),
            (
                19,
                main_account.id,
                transport_category.id,
                Decimal("-6.90"),
                "Bicimad",
                "Dos desplazamientos urbanos",
            ),
            (
                20,
                main_account.id,
                food_category.id,
                Decimal("-14.20"),
                "Menú del día",
                "Comida cerca de la oficina",
            ),
            (
                21,
                shared_account.id,
                leisure_category.id,
                Decimal("-32.00"),
                "Copas sábado",
                "Salida con amigos",
            ),
            (
                23,
                main_account.id,
                food_category.id,
                Decimal("-44.10"),
                "Compra semanal",
                "Supermercado",
            ),
            (
                24,
                main_account.id,
                transfer_category.id,
                Decimal("-150.00"),
                "Ajuste a ahorro",
                "Segunda aportación del mes",
            ),
            (
                24,
                savings_account.id,
                transfer_category.id,
                Decimal("150.00"),
                "Ajuste desde cuenta principal",
                "Entrada correspondiente en ahorro",
            ),
            (
                25,
                main_account.id,
                transport_category.id,
                Decimal("-22.30"),
                "Gasolina",
                "Fin de semana fuera",
            ),
            (
                27,
                main_account.id,
                food_category.id,
                Decimal("-39.95"),
                "Mercadona",
                "Reposición fin de mes",
            ),
            (
                28,
                shared_account.id,
                leisure_category.id,
                Decimal("-58.00"),
                "Brunch y museo",
                "Plan de domingo",
            ),
            (
                29,
                main_account.id,
                food_category.id,
                Decimal("-11.50"),
                "Café de especialidad",
                "Trabajo en remoto",
            ),
            (
                30,
                main_account.id,
                transport_category.id,
                Decimal("-18.50"),
                "Recarga transporte",
                "Último desplazamiento del mes",
            ),
        ]
        monthly_bonus = [
            (1, Decimal("0.00"), "Arranque de ciclo", "Mes sin ingreso variable"),
            (0, Decimal("120.00"), "Bonus cierre trimestral", "Incentivo por objetivos"),
            (0, Decimal("0.00"), "Mes sin bonus", "Solo ingreso fijo"),
            (1, Decimal("180.00"), "Bonus proyecto", "Pago variable puntual"),
            (0, Decimal("90.00"), "Guardia técnica", "Compensación por soporte"),
            (0, Decimal("240.00"), "Retribución variable", "Buen cierre del mes"),
        ]
        transactions: list[Transaction] = []

        for month_offset in range(-5, 1):
            month_reference = add_months(today.replace(day=1), month_offset)
            last_day_of_month = monthrange(month_reference.year, month_reference.month)[1]

            def month_date(
                day: int,
                *,
                base_month: date = month_reference,
                last_day: int = last_day_of_month,
            ) -> date:
                return date(base_month.year, base_month.month, min(day, last_day))

            month_index = month_offset + 5

            for day, account_id, category_id, amount, description, notes in monthly_templates:
                transactions.append(
                    Transaction(
                        user_id=user.id,
                        account_id=account_id,
                        category_id=category_id,
                        date=month_date(day),
                        amount=amount,
                        currency="EUR",
                        description=description,
                        notes=notes,
                    )
                )

            bonus_day, bonus_amount, bonus_description, bonus_notes = monthly_bonus[month_index]
            if bonus_amount != Decimal("0.00"):
                transactions.append(
                    Transaction(
                        user_id=user.id,
                        account_id=main_account.id,
                        category_id=salary_category.id,
                        date=month_date(18 + bonus_day),
                        amount=bonus_amount,
                        currency="EUR",
                        description=bonus_description,
                        notes=bonus_notes,
                    )
                )

        session.add_all(transactions)

        budgets = [
            Budget(
                user_id=user.id,
                category_id=food_category.id,
                year=today.year,
                month=today.month,
                currency="EUR",
                amount=Decimal("350.00"),
            ),
            Budget(
                user_id=user.id,
                category_id=transport_category.id,
                year=today.year,
                month=today.month,
                currency="EUR",
                amount=Decimal("120.00"),
            ),
            Budget(
                user_id=user.id,
                category_id=leisure_category.id,
                year=today.year,
                month=today.month,
                currency="EUR",
                amount=Decimal("180.00"),
            ),
            Budget(
                user_id=user.id,
                category_id=housing_category.id,
                year=today.year,
                month=today.month,
                currency="EUR",
                amount=Decimal("950.00"),
            ),
        ]
        session.add_all(budgets)

        session.commit()

    print("Demo data seeded successfully.")
    print(f"Email: {DEMO_EMAIL}")
    print(f"Password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed_demo_data()
