from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.admin_log import AdminLog
from app.models.project import Project
from app.models.risk_analysis import RiskAnalysis
from app.models.task import Task
from app.models.user import User
from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_team,
    create_team_project,
    create_team_task,
    create_verified_user_and_login,
    login_user,
    make_admin_directly,
    register_user,
)


def create_admin_and_login(
    client: TestClient,
    db: Session,
    username: str = "admin_project_oversight",
    email: str = "admin_project_oversight@example.com",
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


def test_normal_user_cannot_list_admin_projects(
    client: TestClient,
    db: Session,
) -> None:
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="normal_project_viewer",
        email="normal_project_viewer@example.com",
    )

    response = client.get(
        "/admin/projects",
        headers=auth_headers(token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required."


def test_admin_can_list_personal_and_team_projects(
    client: TestClient,
    db: Session,
) -> None:
    owner_id, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="project_oversight_owner",
        email="project_oversight_owner@example.com",
    )

    personal_project = create_personal_project(
        client=client,
        token=owner_token,
        title="Admin Oversight Personal Project",
    )

    create_personal_task(
        client=client,
        token=owner_token,
        project_id=personal_project["project_id"],
        title="Admin Oversight Personal Task",
    )

    team = create_team(
        client=client,
        token=owner_token,
        name="Admin Oversight Team",
    )

    team_project = create_team_project(
        client=client,
        token=owner_token,
        team_id=team["team_id"],
        title="Admin Oversight Team Project",
    )

    create_team_task(
        client=client,
        token=owner_token,
        team_id=team["team_id"],
        project_id=team_project["project_id"],
        assigned_to=owner_id,
        title="Admin Oversight Team Task",
    )

    _, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="project_list_admin",
        email="project_list_admin@example.com",
    )

    response = client.get(
        "/admin/projects?limit=20&offset=0",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text

    projects = response.json()
    project_ids = {project["project_id"] for project in projects}

    assert personal_project["project_id"] in project_ids
    assert team_project["project_id"] in project_ids

    personal_result = next(
        project
        for project in projects
        if project["project_id"] == personal_project["project_id"]
    )

    team_result = next(
        project
        for project in projects
        if project["project_id"] == team_project["project_id"]
    )

    assert personal_result["project_type"] == "personal"
    assert personal_result["team"] is None
    assert personal_result["owner"]["user_id"] == owner_id
    assert personal_result["task_stats"]["total_tasks"] >= 1

    assert team_result["project_type"] == "team"
    assert team_result["team"]["team_id"] == team["team_id"]
    assert team_result["task_stats"]["total_tasks"] >= 1


def test_admin_project_filters_work(
    client: TestClient,
    db: Session,
) -> None:
    _, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="project_filter_owner",
        email="project_filter_owner@example.com",
    )

    create_personal_project(
        client=client,
        token=owner_token,
        title="Unique Filter Personal Alpha",
    )

    team = create_team(
        client=client,
        token=owner_token,
        name="Project Filter Team",
    )

    create_team_project(
        client=client,
        token=owner_token,
        team_id=team["team_id"],
        title="Unique Filter Team Beta",
    )

    _, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="project_filter_admin",
        email="project_filter_admin@example.com",
    )

    personal_response = client.get(
        "/admin/projects?project_type=personal&search=Unique Filter Personal",
        headers=auth_headers(admin_token),
    )

    team_response = client.get(
        f"/admin/projects?project_type=team&team_id={team['team_id']}&search=Unique Filter Team",
        headers=auth_headers(admin_token),
    )

    assert personal_response.status_code == 200, personal_response.text
    assert team_response.status_code == 200, team_response.text

    personal_projects = personal_response.json()
    team_projects = team_response.json()

    assert len(personal_projects) >= 1
    assert all(project["project_type"] == "personal" for project in personal_projects)

    assert len(team_projects) >= 1
    assert all(project["project_type"] == "team" for project in team_projects)
    assert all(project["team"]["team_id"] == team["team_id"] for project in team_projects)


def test_admin_can_read_project_detail_with_latest_risk(
    client: TestClient,
    db: Session,
) -> None:
    _, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="project_detail_owner",
        email="project_detail_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=owner_token,
        title="Project Detail With Risk",
    )

    create_personal_task(
        client=client,
        token=owner_token,
        project_id=project["project_id"],
        title="Project Detail Task",
    )

    risk = RiskAnalysis(
        project_id=project["project_id"],
        risk_level="high",
        predicted_delay_days=5,
        reason="Pytest high risk reason",
        recommendation="Pytest high risk recommendation",
    )

    db.add(risk)
    db.commit()

    _, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="project_detail_admin",
        email="project_detail_admin@example.com",
    )

    response = client.get(
        f"/admin/projects/{project['project_id']}",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["project_id"] == project["project_id"]
    assert data["description"] == "Created during pytest"
    assert data["task_stats"]["total_tasks"] >= 1
    assert data["latest_risk"]["risk_level"] == "high"
    assert data["latest_risk"]["predicted_delay_days"] == 5


def test_admin_can_change_project_status_and_create_admin_log(
    client: TestClient,
    db: Session,
) -> None:
    _, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="project_status_owner",
        email="project_status_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=owner_token,
        title="Project Status Change Target",
    )

    _, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="project_status_admin",
        email="project_status_admin@example.com",
    )

    response = client.patch(
        f"/admin/projects/{project['project_id']}/status",
        headers=auth_headers(admin_token),
        json={"status": "on_hold"},
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["message"] == "Project status updated successfully."
    assert data["project"]["status"] == "on_hold"
    assert data["admin_log_id"] > 0

    db.expire_all()

    updated_project = db.get(Project, project["project_id"])
    assert updated_project is not None
    assert updated_project.status == "on_hold"

    log = db.get(AdminLog, data["admin_log_id"])
    assert log is not None
    assert "changed_project_status" in log.action
    assert f"project_id={project['project_id']}" in log.action


def test_invalid_admin_project_status_returns_validation_error(
    client: TestClient,
    db: Session,
) -> None:
    _, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="invalid_project_status_owner",
        email="invalid_project_status_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=owner_token,
        title="Invalid Project Status Target",
    )

    _, admin_token = create_admin_and_login(
        client=client,
        db=db,
        username="invalid_project_status_admin",
        email="invalid_project_status_admin@example.com",
    )

    response = client.patch(
        f"/admin/projects/{project['project_id']}/status",
        headers=auth_headers(admin_token),
        json={"status": "archived"},
    )

    assert response.status_code == 422
