from __future__ import annotations

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from tests.conftest import (
    auth_headers,
    register_user,
    verify_user_directly,
)


def test_register_user_success(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "username": "authuser",
            "email": "authuser@example.com",
            "password": "Password1!",
            "full_name": "Auth User",
        },
    )

    assert response.status_code == 201
    assert response.json()["message"] == "Registration successful. Please verify your email."


def test_register_rejects_weak_password(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "password",
            "full_name": "Weak User",
        },
    )

    assert response.status_code == 422


def test_login_requires_verified_email(client: TestClient) -> None:
    register_user(
        client,
        username="unverified",
        email="unverified@example.com",
    )

    response = client.post(
        "/auth/login",
        data={
            "username": "unverified@example.com",
            "password": "Password1!",
        },
    )

    assert response.status_code == 403


def test_login_and_me_success(client: TestClient, db: Session) -> None:
    register_user(
        client,
        username="verifieduser",
        email="verified@example.com",
    )
    verify_user_directly(db, "verified@example.com")

    login_response = client.post(
        "/auth/login",
        data={
            "username": "verified@example.com",
            "password": "Password1!",
        },
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/auth/me",
        headers=auth_headers(token),
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "verified@example.com"


def test_protected_route_rejects_missing_token(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_duplicate_email_rejected(client: TestClient) -> None:
    register_user(
        client,
        username="dupuser1",
        email="duplicate@example.com",
    )

    response = client.post(
        "/auth/register",
        json={
            "username": "dupuser2",
            "email": "duplicate@example.com",
            "password": "Password1!",
            "full_name": "Duplicate User",
        },
    )

    assert response.status_code == 409
