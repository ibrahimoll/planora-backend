from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_verified_user_and_login,
    login_user,
    make_admin_directly,
    register_user,
)


def create_admin_and_login(
    client: TestClient,
    db: Session,
    username: str = "admin_user",
    email: str = "admin@example.com",
) -> str:
    register_user(
        client=client,
        username=username,
        email=email,
    )

    make_admin_directly(db, email)

    return login_user(
        client=client,
        username_or_email=email,
    )


def test_normal_user_cannot_access_admin_dashboard(
    client: TestClient,
    db: Session,
) -> None:
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="normal_user",
        email="normal@example.com",
    )

    response = client.get(
        "/admin/dashboard/overview",
        headers=auth_headers(token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required."


def test_admin_can_read_dashboard_overview(
    client: TestClient,
    db: Session,
) -> None:
    _, user_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="project_owner",
        email="owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=user_token,
        title="Admin Dashboard Project",
    )

    create_personal_task(
        client=client,
        token=user_token,
        project_id=project["project_id"],
        title="Admin Dashboard Task",
    )

    admin_token = create_admin_and_login(client=client, db=db)

    response = client.get(
        "/admin/dashboard/overview",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["users"]["total_users"] >= 2
    assert data["users"]["admin_users"] >= 1
    assert data["projects"]["total_projects"] >= 1
    assert data["projects"]["personal_projects"] >= 1
    assert data["tasks"]["total_tasks"] >= 1
    assert "generated_at" in data


def test_admin_can_list_users(
    client: TestClient,
    db: Session,
) -> None:
    create_verified_user_and_login(
        client=client,
        db=db,
        username="listed_user",
        email="listed@example.com",
    )

    admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="list_admin",
        email="list_admin@example.com",
    )

    response = client.get(
        "/admin/users?limit=10&offset=0",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()
    users = data["items"]

    assert isinstance(users, list)
    assert data["total"] >= 2
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert any(user["username"] == "listed_user" for user in users)
    assert any(user["role"] == "admin" for user in users)

def test_admin_can_read_recent_activity_and_admin_logs(
    client: TestClient,
    db: Session,
) -> None:
    admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="logs_admin",
        email="logs_admin@example.com",
    )

    activity_response = client.get(
        "/admin/dashboard/recent-activity?limit=10",
        headers=auth_headers(admin_token),
    )

    admin_logs_response = client.get(
        "/admin/logs?limit=10",
        headers=auth_headers(admin_token),
    )

    assert activity_response.status_code == 200, activity_response.text
    assert admin_logs_response.status_code == 200, admin_logs_response.text

    admin_logs_data = admin_logs_response.json()

    assert isinstance(activity_response.json(), list)
    assert isinstance(admin_logs_data["items"], list)
    assert admin_logs_data["limit"] == 10
    assert admin_logs_data["offset"] == 0
    assert admin_logs_data["total"] >= 0