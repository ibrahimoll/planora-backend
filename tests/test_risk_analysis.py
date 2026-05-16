from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.project import Project
from app.models.task import Task
from app.services.risk_analysis_service import (
    calculate_risk_preview,
    create_risk_analysis_for_project,
    get_project_tasks_for_risk_analysis,
)
from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_verified_user_and_login,
)


def test_preview_project_risk_analysis_route(client, db):
    user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="risk_preview_user",
        email="risk_preview_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Preview Risk Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Preview Risk Task",
    )

    response = client.get(
        f"/projects/{project['project_id']}/risk-analysis/preview",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["project_id"] == project["project_id"]
    assert data["risk_level"] in ["low", "medium", "high"]
    assert data["predicted_delay_days"] >= 0
    assert data["reason"]
    assert data["recommendation"]
    assert data["total_tasks"] == 1


def test_generate_project_risk_analysis_route(client, db):
    user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="risk_generate_user",
        email="risk_generate_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Generate Risk Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Generate Risk Task",
    )

    response = client.post(
        f"/projects/{project['project_id']}/risk-analysis",
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["risk_id"] is not None
    assert data["project_id"] == project["project_id"]
    assert data["risk_level"] in ["low", "medium", "high"]
    assert data["predicted_delay_days"] >= 0
    assert data["reason"]
    assert data["recommendation"]
    assert data["created_at"]


def test_list_project_risk_analyses_route(client, db):
    user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="risk_list_user",
        email="risk_list_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="List Risk Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="List Risk Task",
    )

    create_response = client.post(
        f"/projects/{project['project_id']}/risk-analysis",
        headers=auth_headers(token),
    )

    assert create_response.status_code == 201, create_response.text

    list_response = client.get(
        f"/projects/{project['project_id']}/risk-analysis",
        headers=auth_headers(token),
    )

    assert list_response.status_code == 200, list_response.text

    data = list_response.json()

    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["project_id"] == project["project_id"]
    assert data[0]["risk_level"] in ["low", "medium", "high"]


def test_user_cannot_access_other_users_project_risk_analysis(client, db):
    owner_id, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="risk_owner_user",
        email="risk_owner_user@example.com",
    )

    other_id, other_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="risk_other_user",
        email="risk_other_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=owner_token,
        title="Private Risk Project",
    )

    response = client.get(
        f"/projects/{project['project_id']}/risk-analysis/preview",
        headers=auth_headers(other_token),
    )

    assert response.status_code == 404


def test_calculate_low_risk_for_stable_project(client, db):
    user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="risk_low_user",
        email="risk_low_user@example.com",
    )

    project_data = create_personal_project(
        client=client,
        token=token,
        title="Low Risk Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project_data["project_id"],
        title="Stable Task",
    )

    project = db.get(Project, project_data["project_id"])
    assert project is not None

    tasks = get_project_tasks_for_risk_analysis(
        db=db,
        project_id=project.project_id,
    )

    preview = calculate_risk_preview(
        project=project,
        tasks=tasks,
    )

    assert preview.project_id == project.project_id
    assert preview.risk_level.value == "low"
    assert preview.predicted_delay_days == 0
    assert preview.total_tasks == 1
    assert preview.completed_tasks == 0
    assert preview.overdue_tasks == 0
    assert preview.blocked_tasks == 0


def test_calculate_high_risk_when_task_is_overdue(client, db):
    user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="risk_high_user",
        email="risk_high_user@example.com",
    )

    project_data = create_personal_project(
        client=client,
        token=token,
        title="High Risk Project",
    )

    task_data = create_personal_task(
        client=client,
        token=token,
        project_id=project_data["project_id"],
        title="Overdue Task",
    )

    task = db.get(Task, task_data["task_id"])
    assert task is not None

    task.due_date = datetime.now(timezone.utc) - timedelta(days=2)
    task.estimated_hours = 20
    db.commit()

    project = db.get(Project, project_data["project_id"])
    assert project is not None

    tasks = get_project_tasks_for_risk_analysis(
        db=db,
        project_id=project.project_id,
    )

    preview = calculate_risk_preview(
        project=project,
        tasks=tasks,
    )

    assert preview.risk_level.value == "high"
    assert preview.overdue_tasks == 1
    assert preview.predicted_delay_days >= 0


def test_create_risk_analysis_saves_record(client, db):
    user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="risk_save_user",
        email="risk_save_user@example.com",
    )

    project_data = create_personal_project(
        client=client,
        token=token,
        title="Saved Risk Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project_data["project_id"],
        title="Task For Saved Risk",
    )

    project = db.get(Project, project_data["project_id"])
    assert project is not None

    risk_analysis = create_risk_analysis_for_project(
        db=db,
        project=project,
    )

    assert risk_analysis.risk_id is not None
    assert risk_analysis.project_id == project.project_id
    assert risk_analysis.risk_level in ["low", "medium", "high"]
    assert risk_analysis.predicted_delay_days >= 0
    assert risk_analysis.reason
    assert risk_analysis.recommendation