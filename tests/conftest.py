from __future__ import annotations

import os
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app

# Import all models so SQLAlchemy can create every table during tests.
import app.models  # noqa: F401

load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

engine = None
TestingSessionLocal = None

if TEST_DATABASE_URL:
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )


def _require_test_database() -> None:
    if not TEST_DATABASE_URL or engine is None or TestingSessionLocal is None:
        pytest.skip(
            "TEST_DATABASE_URL is not set. Set it to your PostgreSQL test database URL."
        )


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database() -> Generator[None, None, None]:
    if not TEST_DATABASE_URL or engine is None:
        yield
        return

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    _require_test_database()

    assert engine is not None
    assert TestingSessionLocal is not None

    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def disable_outbound_email(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.auth_service as auth_service

    monkeypatch.setattr(
        auth_service,
        "send_verification_email",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        auth_service,
        "send_password_reset_email",
        lambda *args, **kwargs: None,
    )


@pytest.fixture(autouse=True)
def clear_rate_limits() -> None:
    try:
        from app.core.rate_limit import _requests

        _requests.clear()
    except Exception:
        pass


def future_iso(days: int = 7) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_user(
    client: TestClient,
    username: str,
    email: str,
    password: str = "Password1!",
    full_name: str | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "full_name": full_name or username.replace("_", " ").title(),
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def verify_user_directly(db: Session, email: str) -> None:
    from app.models.user import User

    user = db.query(User).filter(User.email == email.lower()).first()
    assert user is not None

    user.is_email_verified = True
    db.commit()


def make_admin_directly(db: Session, email: str) -> None:
    from app.models.user import User

    user = db.query(User).filter(User.email == email.lower()).first()
    assert user is not None

    user.role = "admin"
    user.is_email_verified = True
    db.commit()


def login_user(
    client: TestClient,
    username_or_email: str,
    password: str = "Password1!",
) -> str:
    response = client.post(
        "/auth/login",
        data={
            "username": username_or_email,
            "password": password,
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["access_token"]

    return data["access_token"]


def create_verified_user_and_login(
    client: TestClient,
    db: Session,
    username: str,
    email: str,
    password: str = "Password1!",
) -> tuple[int, str]:
    register_user(
        client=client,
        username=username,
        email=email,
        password=password,
    )
    verify_user_directly(db, email)

    token = login_user(
        client=client,
        username_or_email=email,
        password=password,
    )

    me_response = client.get(
        "/auth/me",
        headers=auth_headers(token),
    )

    assert me_response.status_code == 200, me_response.text

    return me_response.json()["user_id"], token


def create_personal_project(
    client: TestClient,
    token: str,
    title: str = "Personal Project Test",
) -> dict[str, Any]:
    response = client.post(
        "/projects",
        headers=auth_headers(token),
        json={
            "title": title,
            "description": "Created during pytest",
            "deadline": future_iso(7),
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_personal_task(
    client: TestClient,
    token: str,
    project_id: int,
    title: str = "Personal Task Test",
) -> dict[str, Any]:
    response = client.post(
        f"/projects/{project_id}/tasks",
        headers=auth_headers(token),
        json={
            "title": title,
            "description": "Created during pytest",
            "priority": "medium",
            "estimated_hours": 2,
            "due_date": future_iso(3),
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_team(
    client: TestClient,
    token: str,
    name: str = "Pytest Team",
) -> dict[str, Any]:
    response = client.post(
        "/teams",
        headers=auth_headers(token),
        json={"name": name},
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_team_project(
    client: TestClient,
    token: str,
    team_id: int,
    title: str = "Pytest Team Project",
) -> dict[str, Any]:
    response = client.post(
        f"/teams/{team_id}/projects",
        headers=auth_headers(token),
        json={
            "title": title,
            "description": "Created during pytest",
            "deadline": future_iso(10),
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_team_task(
    client: TestClient,
    token: str,
    team_id: int,
    project_id: int,
    assigned_to: int | None = None,
    title: str = "Pytest Team Task",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "title": title,
        "description": "Created during pytest",
        "priority": "high",
        "estimated_hours": 4,
        "due_date": future_iso(4),
    }

    if assigned_to is not None:
        body["assigned_to"] = assigned_to

    response = client.post(
        f"/teams/{team_id}/projects/{project_id}/tasks",
        headers=auth_headers(token),
        json=body,
    )

    assert response.status_code == 201, response.text
    return response.json()
