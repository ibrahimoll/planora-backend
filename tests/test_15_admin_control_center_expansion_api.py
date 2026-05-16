from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.admin_log import AdminLog
from app.models.risk_analysis import RiskAnalysis
from app.models.task import Task
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
    username: str = "admin_expansion",
    email: str = "admin_expansion@example.com",
) -> tuple[int, str]:
    register_user(client=client, username=username, email=email)
    make_admin_directly(db, email)
    token = login_user(client=client, username_or_email=email)

    admin = db.query(User).filter(User.email == email.lower()).first()
    assert admin is not None

    return admin.user_id, token


def test_admin_can_filter_users_and_logs(
    client: TestClient,
    db: Session,
) -> None:
    target_user_id, _ = create_verified_user_and_login(
        client=client,
        db=db,
        username="filter_target_user",
        email="filter_target_user@example.com",
    )

    admin_id, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="filter_admin_user",
        email="filter_admin_user@example.com",
    )

    log = AdminLog(
        admin_id=admin_id,
        target_user_id=target_user_id,
        action="pytest_filter_action",
    )
    db.add(log)
    db.commit()

    users_response = client.get(
        "/admin/users?role=user&is_active=true&is_email_verified=true&search=filter_target",
        headers=auth_headers(admin_token),
    )

    logs_response = client.get(
        f"/admin/logs?action=pytest_filter_action&target_user_id={target_user_id}",
        headers=auth_headers(admin_token),
    )

    assert users_response.status_code == 200, users_response.text
    assert logs_response.status_code == 200, logs_response.text

    assert any(user["user_id"] == target_user_id for user in users_response.json())
    assert any(item["action"] == "pytest_filter_action" for item in logs_response.json())


def test_admin_can_view_user_activity(
    client: TestClient,
    db: Session,
) -> None:
    user_id, user_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_target_user",
        email="activity_target_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=user_token,
        title="Admin Activity Project",
    )

    activity = ActivityLog(
        project_id=project["project_id"],
        actor_id=user_id,
        event_type="project_created",
        actor_username_snapshot="activity_target_user",
        actor_full_name_snapshot="Activity Target User",
        message="User created project for admin activity test",
    )
    db.add(activity)
    db.commit()

    _, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="activity_admin_user",
        email="activity_admin_user@example.com",
    )

    response = client.get(
        f"/admin/users/{user_id}/activity",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text
    assert any(item["actor_id"] == user_id for item in response.json())


def test_admin_task_oversight_status_and_assignment(
    client: TestClient,
    db: Session,
) -> None:
    owner_id, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="admin_task_owner",
        email="admin_task_owner@example.com",
    )

    new_assignee_id, _ = create_verified_user_and_login(
        client=client,
        db=db,
        username="admin_task_assignee",
        email="admin_task_assignee@example.com",
    )

    project = create_personal_project(
        client=client,
        token=owner_token,
        title="Admin Task Oversight Project",
    )

    task = create_personal_task(
        client=client,
        token=owner_token,
        project_id=project["project_id"],
        title="Admin Task Oversight Target",
    )

    _, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="task_oversight_admin_user",
        email="task_oversight_admin_user@example.com",
    )

    list_response = client.get(
        "/admin/tasks?search=Admin Task Oversight Target",
        headers=auth_headers(admin_token),
    )
    status_response = client.patch(
        f"/admin/tasks/{task['task_id']}/status",
        headers=auth_headers(admin_token),
        json={"status": "blocked"},
    )
    assignment_response = client.patch(
        f"/admin/tasks/{task['task_id']}/assignment",
        headers=auth_headers(admin_token),
        json={"assigned_to": new_assignee_id},
    )

    assert list_response.status_code == 200, list_response.text
    assert status_response.status_code == 200, status_response.text
    assert assignment_response.status_code == 200, assignment_response.text

    assert any(item["task_id"] == task["task_id"] for item in list_response.json())
    assert status_response.json()["task"]["status"] == "blocked"
    assert assignment_response.json()["task"]["assignee"]["user_id"] == new_assignee_id

    db.expire_all()
    updated_task = db.get(Task, task["task_id"])
    assert updated_task is not None
    assert updated_task.assigned_to == new_assignee_id
    assert owner_id != new_assignee_id


def test_admin_risk_center_and_reports(
    client: TestClient,
    db: Session,
) -> None:
    _, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="risk_report_owner",
        email="risk_report_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=owner_token,
        title="Risk Report Project",
    )

    task = create_personal_task(
        client=client,
        token=owner_token,
        project_id=project["project_id"],
        title="Risk Report Blocked Task",
    )

    db_task = db.get(Task, task["task_id"])
    assert db_task is not None
    db_task.status = "blocked"
    db_task.due_date = datetime.now(timezone.utc) - timedelta(days=2)

    risk = RiskAnalysis(
        project_id=project["project_id"],
        risk_level="high",
        predicted_delay_days=4,
        reason="Pytest high risk reason",
        recommendation="Pytest high risk recommendation",
    )
    db.add(risk)
    db.commit()

    _, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="risk_report_admin_user",
        email="risk_report_admin_user@example.com",
    )

    risk_summary_response = client.get(
        "/admin/risk/summary",
        headers=auth_headers(admin_token),
    )
    high_risk_response = client.get(
        "/admin/risk/high-risk-projects",
        headers=auth_headers(admin_token),
    )
    system_report_response = client.get(
        "/admin/reports/system-summary",
        headers=auth_headers(admin_token),
    )

    assert risk_summary_response.status_code == 200, risk_summary_response.text
    assert high_risk_response.status_code == 200, high_risk_response.text
    assert system_report_response.status_code == 200, system_report_response.text

    assert risk_summary_response.json()["high_risk_projects"] >= 1
    assert any(item["project"]["project_id"] == project["project_id"] for item in high_risk_response.json())
    assert system_report_response.json()["blocked_tasks"] >= 1


def test_normal_user_cannot_access_admin_expansion_routes(
    client: TestClient,
    db: Session,
) -> None:
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="normal_admin_expansion_user",
        email="normal_admin_expansion_user@example.com",
    )

    response = client.get(
        "/admin/risk/summary",
        headers=auth_headers(token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required."
