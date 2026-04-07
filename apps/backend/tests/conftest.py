import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User

TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def enable_dev_user_header_for_tests() -> Generator[None, None, None]:
    original = settings.allow_dev_user_header
    settings.allow_dev_user_header = True
    try:
        yield
    finally:
        settings.allow_dev_user_header = original


@pytest.fixture(autouse=True)
def disable_require_llm_for_tests() -> Generator[None, None, None]:
    original = settings.monthly_recap_require_llm
    settings.monthly_recap_require_llm = False
    try:
        yield
    finally:
        settings.monthly_recap_require_llm = original


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def user_id() -> uuid.UUID:
    user = User(
        auth_provider_user_id=f"test-{uuid.uuid4()}",
        email=f"user-{uuid.uuid4()}@example.com",
        name="Test User",
    )

    with TestingSessionLocal() as db:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id
