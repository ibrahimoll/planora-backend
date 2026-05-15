from __future__ import annotations

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_verified_user_and_login,
)


def test_profile_route_available(client: TestClient, db: Session) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username="profileuser",
        email="profileuser@example.com",
    )

    response = client.get(
        "/profile",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["email"] == "profileuser@example.com"


def test_attachment_routes_are_protected(client: TestClient) -> None:
    response = client.get("/projects/1/attachments")

    assert response.status_code == 401


def test_personal_project_task_exists_for_attachment_tests(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username="attachuser",
        email="attachuser@example.com",
    )

    project = create_personal_project(client, token)
    task = create_personal_task(client, token, project["project_id"])

    assert project["project_id"] is not None
    assert task["task_id"] is not None
