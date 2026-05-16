from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.admin_log import AdminLog
from app.models.user import User
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
    username: str = "admin_user_step_23",
    email: str = "admin_step_23@example.com",
) -> tuple[int, str]:
    register_user(
        client=client,
        username=username,
        email=email,
    )

    make_admin_directly(db, email)

    token = login_user(
        client=client,
        username_or_email=email,
    )

    admin = db.query(User).filter(User.email == email.lower()).first()
    assert admin is not None

    return admin.user_id, token


def test_normal_user_cannot_read_admin_user_detail(
    client: TestClient,
    db: Session,
) -> None:
    target_user_id, _ = create_verified_user_and_login(
        client=client,
        db=db,
        username="admin_detail_target",
        email="admin_detail_target@example.com",
    )

    _, normal_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="normal_detail_reader",
        email="normal_detail_reader@example.com",
    )

    response = client.get(
        f"/admin/users/{target_user_id}",
        headers=auth_headers(normal_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required."


def test_admin_can_read_user_detail_with_counts(
    client: TestClient,
    db: Session,
) -> None:
    target_user_id, target_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="detail_count_user",
        email="detail_count_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=target_token,
        title="Detail Count Project",
    )

    create_personal_task(
        client=client,
        token=target_token,
        project_id=project["project_id"],
        title="Detail Count Task",
    )

    _, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="detail_count_admin",
        email="detail_count_admin@example.com",
    )

    response = client.get(
        f"/admin/users/{target_user_id}",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["user_id"] == target_user_id
    assert data["username"] == "detail_count_user"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert data["counts"]["projects_created"] >= 1
    assert data["counts"]["assigned_tasks"] >= 1
    assert data["counts"]["created_tasks"] >= 1


def test_admin_can_deactivate_and_activate_user_with_logs(
    client: TestClient,
    db: Session,
) -> None:
    target_user_id, _ = create_verified_user_and_login(
        client=client,
        db=db,
        username="activate_target_user",
        email="activate_target_user@example.com",
    )

    _, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="activate_admin",
        email="activate_admin@example.com",
    )

    deactivate_response = client.patch(
        f"/admin/users/{target_user_id}/deactivate",
        headers=auth_headers(admin_token),
    )

    assert deactivate_response.status_code == 200, deactivate_response.text
    assert deactivate_response.json()["user"]["is_active"] is False

    db.expire_all()
    target = db.get(User, target_user_id)
    assert target is not None
    assert target.is_active is False

    activate_response = client.patch(
        f"/admin/users/{target_user_id}/activate",
        headers=auth_headers(admin_token),
    )

    assert activate_response.status_code == 200, activate_response.text
    assert activate_response.json()["user"]["is_active"] is True

    db.expire_all()
    target = db.get(User, target_user_id)
    assert target is not None
    assert target.is_active is True

    logs = (
        db.query(AdminLog)
        .filter(AdminLog.target_user_id == target_user_id)
        .order_by(AdminLog.created_at.asc())
        .all()
    )

    actions = [log.action for log in logs]

    assert any("deactivated_user" in action for action in actions)
    assert any("activated_user" in action for action in actions)


def test_admin_cannot_deactivate_self(
    client: TestClient,
    db: Session,
) -> None:
    admin_user_id, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="self_deactivate_admin",
        email="self_deactivate_admin@example.com",
    )

    response = client.patch(
        f"/admin/users/{admin_user_id}/deactivate",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "You cannot deactivate your own admin account."


def test_admin_can_promote_user_to_admin(
    client: TestClient,
    db: Session,
) -> None:
    target_user_id, target_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="promote_target_user",
        email="promote_target_user@example.com",
    )

    _, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="promote_admin",
        email="promote_admin@example.com",
    )

    response = client.patch(
        f"/admin/users/{target_user_id}/role",
        headers=auth_headers(admin_token),
        json={"role": "admin"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["role"] == "admin"

    db.expire_all()
    target = db.get(User, target_user_id)
    assert target is not None
    assert target.role == "admin"

    dashboard_response = client.get(
        "/admin/dashboard/overview",
        headers=auth_headers(target_token),
    )

    assert dashboard_response.status_code == 200, dashboard_response.text


def test_admin_can_demote_another_admin_to_user(
    client: TestClient,
    db: Session,
) -> None:
    _, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="main_demote_admin",
        email="main_demote_admin@example.com",
    )

    target_admin_id, _ = create_admin_and_login(
        client=client,
        db=db,
        username="target_demote_admin",
        email="target_demote_admin@example.com",
    )

    response = client.patch(
        f"/admin/users/{target_admin_id}/role",
        headers=auth_headers(admin_token),
        json={"role": "user"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["role"] == "user"

    db.expire_all()
    target_admin = db.get(User, target_admin_id)
    assert target_admin is not None
    assert target_admin.role == "user"


def test_admin_cannot_demote_self(
    client: TestClient,
    db: Session,
) -> None:
    admin_user_id, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="self_demote_admin",
        email="self_demote_admin@example.com",
    )

    response = client.patch(
        f"/admin/users/{admin_user_id}/role",
        headers=auth_headers(admin_token),
        json={"role": "user"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "You cannot remove your own admin role."


def test_invalid_admin_role_returns_validation_error(
    client: TestClient,
    db: Session,
) -> None:
    target_user_id, _ = create_verified_user_and_login(
        client=client,
        db=db,
        username="invalid_role_target",
        email="invalid_role_target@example.com",
    )

    _, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="invalid_role_admin",
        email="invalid_role_admin@example.com",
    )

    response = client.patch(
        f"/admin/users/{target_user_id}/role",
        headers=auth_headers(admin_token),
        json={"role": "owner"},
    )

    assert response.status_code == 422
