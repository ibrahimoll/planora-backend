from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_verified_user_and_login,
    login_user,
    make_admin_directly,
    register_user,
    verify_user_directly,
)


def _create_admin_token(client: TestClient, db: Session) -> str:
    email = "pagination_admin@example.com"

    register_user(
        client=client,
        username="pagination_admin",
        email=email,
    )
    make_admin_directly(db, email)

    return login_user(client=client, username_or_email=email)


def test_admin_users_include_pagination_metadata(
    client: TestClient,
    db: Session,
) -> None:
    admin_token = _create_admin_token(client=client, db=db)

    for index in range(3):
        email = f"pagination_user_{index}@example.com"
        register_user(
            client=client,
            username=f"pagination_user_{index}",
            email=email,
        )
        verify_user_directly(db, email)

    response = client.get(
        "/admin/users?limit=2&offset=0",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert set(data.keys()) == {"items", "total", "limit", "offset"}
    assert data["total"] == 4
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) == 2


def test_admin_users_pagination_count_respects_filters(
    client: TestClient,
    db: Session,
) -> None:
    admin_token = _create_admin_token(client=client, db=db)

    response = client.get(
        "/admin/users?role=admin&limit=10&offset=0",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["role"] == "admin"


def test_admin_projects_include_total_count(
    client: TestClient,
    db: Session,
) -> None:
    admin_token = _create_admin_token(client=client, db=db)

    _, user_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="pagination_project_owner",
        email="pagination_project_owner@example.com",
    )

    for index in range(3):
        create_personal_project(
            client=client,
            token=user_token,
            title=f"Pagination Project {index}",
        )

    response = client.get(
        "/admin/projects?limit=2&offset=0",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["total"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) == 2


def test_admin_tasks_include_total_count(
    client: TestClient,
    db: Session,
) -> None:
    admin_token = _create_admin_token(client=client, db=db)

    _, user_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="pagination_task_owner",
        email="pagination_task_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=user_token,
        title="Pagination Task Project",
    )

    for index in range(3):
        create_personal_task(
            client=client,
            token=user_token,
            project_id=project["project_id"],
            title=f"Pagination Task {index}",
        )

    response = client.get(
        "/admin/tasks?limit=2&offset=0",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["total"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) == 2


def test_admin_logs_include_total_count(
    client: TestClient,
    db: Session,
) -> None:
    admin_token = _create_admin_token(client=client, db=db)

    user = register_user(
        client=client,
        username="pagination_log_target",
        email="pagination_log_target@example.com",
    )
    verify_user_directly(db, "pagination_log_target@example.com")

    deactivate_response = client.patch(
        f"/admin/users/{user['user_id']}/deactivate",
        headers=auth_headers(admin_token),
    )

    assert deactivate_response.status_code == 200, deactivate_response.text

    response = client.get(
        "/admin/logs?limit=1&offset=0",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["total"] == 1
    assert data["limit"] == 1
    assert data["offset"] == 0
    assert len(data["items"]) == 1
