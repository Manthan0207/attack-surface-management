"""Pytest fixtures for the ASM Asset Discovery Service."""

from __future__ import annotations

import os

# Must be set before application modules are imported.
os.environ["TESTING"] = "true"
os.environ.setdefault("JWT_SECRET_KEY", "pytest-secret")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "ChangeMeAdmin123!")
os.environ.setdefault("ADMIN_FULL_NAME", "Platform Admin")
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://asm:asm@localhost:5432/asm_test",
    ),
)


def _ensure_database_exists(database_url: str) -> None:
    """Create the target database if it does not already exist."""
    from sqlalchemy import create_engine, text

    db_name = database_url.rsplit("/", 1)[-1]
    admin_url = database_url.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        admin_engine.dispose()


_ensure_database_exists(os.environ["DATABASE_URL"])

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine, get_db
from app.core.rate_limit import reset_rate_limits
from app.core.security import hash_password
from app.main import create_app
from app.models.asset import AssetType
from app.models.user import User, UserRole
from app.workers.discovery import _process_scan


@pytest.fixture(scope="session", autouse=True)
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_tables() -> Generator[None, None, None]:
    """Truncate all tables between tests for isolation."""
    reset_rate_limits()
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    reset_rate_limits()


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sync_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run discovery inline instead of using the background queue."""

    def _immediate(scan_id: str) -> None:
        _process_scan(scan_id)

    monkeypatch.setattr("app.services.scan.enqueue_scan", _immediate)
    monkeypatch.setattr(
        "app.workers.discovery.resolve_domain_records",
        lambda _name: [
            (AssetType.A, "93.184.216.34"),
            (AssetType.AAAA, "2606:2800:220:1:248:1893:25c8:1946"),
            (AssetType.NS, "a.iana-servers.net"),
            (AssetType.MX, "mail.example.com"),
        ],
    )


@pytest.fixture
def client(sync_discovery: None) -> Generator[TestClient, None, None]:
    app = create_app()

    def _override_get_db() -> Generator[Session, None, None]:
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_user(db: Session, *, email: str, password: str, role: UserRole) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=f"{role.value.title()} User",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def analyst_headers(client: TestClient, db: Session) -> dict[str, str]:
    _create_user(
        db,
        email="analyst@example.com",
        password="AnalystPass1!",
        role=UserRole.ANALYST,
    )
    response = client.post(
        "/auth/login",
        json={"email": "analyst@example.com", "password": "AnalystPass1!"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def viewer_headers(client: TestClient, db: Session) -> dict[str, str]:
    _create_user(
        db,
        email="viewer@example.com",
        password="ViewerPass1!",
        role=UserRole.VIEWER,
    )
    response = client.post(
        "/auth/login",
        json={"email": "viewer@example.com", "password": "ViewerPass1!"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
