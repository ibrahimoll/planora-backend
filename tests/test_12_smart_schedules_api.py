from __future__ import annotations

from app.models.smart_schedule import SmartSchedule
from app.models.task import Task
from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_team,
    create_team_project,
    create_team_task,
    create_verified_user_and_login,
)


def test_preview_personal_project_smart_schedule_route(client, db):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="schedule_preview_user",
        email="schedule_preview_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Preview Smart Schedule Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Preview Smart Schedule Task",
    )

    response = client.post(
        f"/projects/{project['project_id']}/smart-schedules/preview",
        headers=auth_headers(token),
        json={},
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["project_id"] == project["project_id"]
    assert data["strategy"] == "balanced"
    assert data["daily_capacity_hours"] == 4.0
    assert data["total_tasks"] == 1
    assert data["schedulable_task_count"] == 1
    assert data["completed_task_count"] == 0
    assert data["estimated_total_hours"] > 0
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["title"] == "Preview Smart Schedule Task"
    assert data["tasks"][0]["suggested_due_date"]


def test_generate_personal_project_smart_schedule_saves_record(client, db):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="schedule_generate_user",
        email="schedule_generate_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Generate Smart Schedule Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Generate Smart Schedule Task",
    )

    response = client.post(
        f"/projects/{project['project_id']}/smart-schedules",
        headers=auth_headers(token),
        json={
            "daily_capacity_hours": 4,
            "apply_schedule": False,
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["schedule_id"] is not None
    assert data["project_id"] == project["project_id"]
    assert data["generated_by"] is not None
    assert data["strategy"] == "balanced"
    assert data["applied_at"] is None
    assert data["schedule_data"]["project_id"] == project["project_id"]
    assert len(data["schedule_data"]["tasks"]) == 1

    saved_schedule = db.get(SmartSchedule, data["schedule_id"])

    assert saved_schedule is not None
    assert saved_schedule.project_id == project["project_id"]


def test_apply_personal_project_smart_schedule_updates_task_due_date(client, db):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="schedule_apply_user",
        email="schedule_apply_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Apply Smart Schedule Project",
    )

    task_data = create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Apply Smart Schedule Task",
    )

    task = db.get(Task, task_data["task_id"])
    assert task is not None

    task.due_date = None
    db.commit()

    response = client.post(
        f"/projects/{project['project_id']}/smart-schedules",
        headers=auth_headers(token),
        json={
            "daily_capacity_hours": 4,
            "apply_schedule": True,
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["applied_at"] is not None
    assert task_data["task_id"] in data["schedule_data"]["applied_task_ids"]

    db.refresh(task)

    assert task.due_date is not None


def test_user_cannot_preview_other_users_personal_project_smart_schedule(client, db):
    _owner_id, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="schedule_owner_user",
        email="schedule_owner_user@example.com",
    )

    _other_id, other_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="schedule_other_user",
        email="schedule_other_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=owner_token,
        title="Private Smart Schedule Project",
    )

    response = client.post(
        f"/projects/{project['project_id']}/smart-schedules/preview",
        headers=auth_headers(other_token),
        json={},
    )

    assert response.status_code == 404


def test_team_project_owner_can_generate_smart_schedule(client, db):
    owner_id, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="schedule_team_owner",
        email="schedule_team_owner@example.com",
    )

    team = create_team(
        client=client,
        token=owner_token,
        name="Smart Schedule Team",
    )

    project = create_team_project(
        client=client,
        token=owner_token,
        team_id=team["team_id"],
        title="Team Smart Schedule Project",
    )

    create_team_task(
        client=client,
        token=owner_token,
        team_id=team["team_id"],
        project_id=project["project_id"],
        assigned_to=owner_id,
        title="Team Smart Schedule Task",
    )

    response = client.post(
        f"/teams/{team['team_id']}/projects/{project['project_id']}/smart-schedules",
        headers=auth_headers(owner_token),
        json={
            "daily_capacity_hours": 4,
            "apply_schedule": False,
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["project_id"] == project["project_id"]
    assert data["strategy"] == "balanced"
    assert len(data["schedule_data"]["tasks"]) == 1


def test_missing_token_cannot_preview_smart_schedule(client, db):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="schedule_missing_token_user",
        email="schedule_missing_token_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Missing Token Smart Schedule Project",
    )

    response = client.post(
        f"/projects/{project['project_id']}/smart-schedules/preview",
        json={},
    )

    assert response.status_code == 401
