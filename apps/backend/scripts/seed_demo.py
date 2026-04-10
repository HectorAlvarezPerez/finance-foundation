from __future__ import annotations

import random
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
DEMO_NAME = "Berta (Estudiante Mates)"


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
            name="ImaginBank (Principal)",
            bank_name="CaixaBank",
            type=AccountType.CHECKING,
            currency="EUR",
        )
        savings_account = Account(
            user_id=user.id,
            name="Hucha (Viaje Verano)",
            bank_name="Revolut",
            type=AccountType.SAVINGS,
            currency="EUR",
        )
        shared_account = Account(
            user_id=user.id,
            name="Fondo Piso (Gràcia)",
            bank_name="N26",
            type=AccountType.SHARED,
            currency="EUR",
        )
        session.add_all([main_account, savings_account, shared_account])
        session.flush()

        salary_category = Category(
            user_id=user.id,
            name="Nómina Camarera",
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
            name="Piso Gràcia",
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
            icon="glass-water",
        )
        education_category = Category(
            user_id=user.id,
            name="Universidad",
            type=CategoryType.EXPENSE,
            color="#eab308",
            icon="book",
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
                education_category,
                transfer_category,
            ]
        )
        session.flush()

        transactions: list[Transaction] = []

        # --- AÑADIR SALDO INICIAL PARA EVITAR CUENTAS EN NEGATIVO ---
        initial_date = add_months(today.replace(day=1), -6)
        transactions.append(
            Transaction(
                user_id=user.id,
                account_id=main_account.id,
                category_id=salary_category.id,
                date=initial_date,
                amount=Decimal("1250.00"),
                currency="EUR",
                description="Saldo Inicial",
                notes="Ahorros acumulados pre-curso",
            )
        )
        transactions.append(
            Transaction(
                user_id=user.id,
                account_id=savings_account.id,
                category_id=salary_category.id,
                date=initial_date,
                amount=Decimal("350.00"),
                currency="EUR",
                description="Ahorro Inicial",
                notes="Fondo reservado",
            )
        )
        transactions.append(
            Transaction(
                user_id=user.id,
                account_id=shared_account.id,
                category_id=salary_category.id,
                date=initial_date,
                amount=Decimal("150.00"),
                currency="EUR",
                description="Fondo Piso Inicial",
                notes="Bote común piso",
            )
        )

        # Generar 6 meses de historial
        for month_offset in range(-5, 1):
            month_reference = add_months(today.replace(day=1), month_offset)
            last_day_of_month = monthrange(month_reference.year, month_reference.month)[1]

            def month_date(day: int, mr=month_reference, ld=last_day_of_month) -> date:
                return date(mr.year, mr.month, min(day, ld))

            savings_goal = Decimal(str(random.choice([0, 20, 50, 80])))

            # 1. INGRESOS (Incrementados para mantener la cuenta en positivo)
            base_salary = 780.00
            extra_hours = random.choice([0, 0, 40, 60, 90])
            monthly_income = Decimal(str(base_salary + extra_hours))

            transactions.append(
                Transaction(
                    user_id=user.id,
                    account_id=main_account.id,
                    category_id=salary_category.id,
                    date=month_date(1),
                    amount=monthly_income,
                    currency="EUR",
                    description="Nómina Cafetería",
                    notes="Ingreso fijo + propinas mes anterior",
                )
            )

            # 2. GASTOS FIJOS (Alquiler rebajado un poco para equilibrar balanza)
            transactions.append(
                Transaction(
                    user_id=user.id,
                    account_id=main_account.id,
                    category_id=housing_category.id,
                    date=month_date(2),
                    amount=Decimal("-380.00"),
                    currency="EUR",
                    description="Alquiler habitación",
                    notes="Transferencia compañero de piso",
                )
            )

            utilities = Decimal(str(random.randint(35, 50)))
            transactions.append(
                Transaction(
                    user_id=user.id,
                    account_id=shared_account.id,
                    category_id=housing_category.id,
                    date=month_date(15),
                    amount=-utilities,
                    currency="EUR",
                    description="Luz e Internet",
                    notes="Parte proporcional",
                )
            )

            if month_offset in [-5, -3, -1]:
                transactions.append(
                    Transaction(
                        user_id=user.id,
                        account_id=main_account.id,
                        category_id=education_category.id,
                        date=month_date(10),
                        amount=Decimal("-180.00"),
                        currency="EUR",
                        description="Pago fraccionado UB",
                        notes="Tercer plazo matrícula",
                    )
                )

            if month_offset in [-5, -2, 1]:
                transactions.append(
                    Transaction(
                        user_id=user.id,
                        account_id=main_account.id,
                        category_id=transport_category.id,
                        date=month_date(5),
                        amount=Decimal("-40.00"),
                        currency="EUR",
                        description="T-Jove TMB",
                        notes="Abono trimestral zonas 1-6",
                    )
                )
            else:
                bicing = Decimal(str(random.randint(3, 10)))
                transactions.append(
                    Transaction(
                        user_id=user.id,
                        account_id=main_account.id,
                        category_id=transport_category.id,
                        date=month_date(14),
                        amount=-bicing,
                        currency="EUR",
                        description="Bicing",
                        notes="Trayectos extra",
                    )
                )

            groceries_total = Decimal("0.00")
            for day in sorted(random.sample(range(6, 28), random.randint(3, 4))):
                amount = (
                    Decimal(str(random.randint(25, 55))) + Decimal(str(random.randint(0, 99))) / 100
                )
                groceries_total += amount
                store = random.choice(["Mercadona", "BonÀrea", "Ametller (Poco)"])
                transactions.append(
                    Transaction(
                        user_id=user.id,
                        account_id=main_account.id,
                        category_id=food_category.id,
                        date=month_date(day),
                        amount=-amount,
                        currency="EUR",
                        description=f"Compra {store}",
                        notes="Supermercado semana",
                    )
                )

            leisure_events = random.randint(3, 6) if extra_hours > 0 else random.randint(1, 3)
            for day in sorted(random.sample(range(3, 28), leisure_events)):
                events = [
                    ("Bravas Tomás", random.randint(12, 18)),
                    ("Cervezas Razzmattazz", random.randint(15, 30)),
                    ("Cine Phenomena", random.randint(9, 12)),
                    ("Café libreria Itaca", random.randint(4, 8)),
                    ("Pizza a medias", random.randint(10, 15)),
                    ("Cena barata VIPS", random.randint(15, 22)),
                ]
                event_name, event_amount = random.choice(events)
                amount_dec = Decimal(str(event_amount)) + Decimal(str(random.randint(0, 99))) / 100
                account_to_charge = (
                    shared_account.id if "medias" in event_name.lower() else main_account.id
                )

                transactions.append(
                    Transaction(
                        user_id=user.id,
                        account_id=account_to_charge,
                        category_id=leisure_category.id,
                        date=month_date(day),
                        amount=-amount_dec,
                        currency="EUR",
                        description=event_name,
                        notes="Salida con la uni",
                    )
                )

            if savings_goal > 0 and monthly_income > 700:
                transactions.append(
                    Transaction(
                        user_id=user.id,
                        account_id=main_account.id,
                        category_id=transfer_category.id,
                        date=month_date(28),
                        amount=-savings_goal,
                        currency="EUR",
                        description="Hucha Viaje",
                        notes="Objetivo verano",
                    )
                )
                transactions.append(
                    Transaction(
                        user_id=user.id,
                        account_id=savings_account.id,
                        category_id=transfer_category.id,
                        date=month_date(28),
                        amount=savings_goal,
                        currency="EUR",
                        description="Ingreso hucha",
                        notes="Desde cuenta principal",
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
                amount=Decimal("180.00"),
            ),
            Budget(
                user_id=user.id,
                category_id=transport_category.id,
                year=today.year,
                month=today.month,
                currency="EUR",
                amount=Decimal("40.00"),
            ),
            Budget(
                user_id=user.id,
                category_id=leisure_category.id,
                year=today.year,
                month=today.month,
                currency="EUR",
                amount=Decimal("100.00"),
            ),
            Budget(
                user_id=user.id,
                category_id=housing_category.id,
                year=today.year,
                month=today.month,
                currency="EUR",
                amount=Decimal("450.00"),
            ),
        ]
        session.add_all(budgets)
        session.commit()

    print("Demo data seeded successfully (Student Profile Barcelona).")
    print(f"Email: {DEMO_EMAIL}")
    print(f"Password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed_demo_data()
