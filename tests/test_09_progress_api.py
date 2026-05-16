from __future__ import annotations

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_team,
    create_team_project,
    create_team_task,
    create_verified_user_and_login,
)


def test_get_personal_project_progress_success(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username="progressowner",
        email="progressowner@example.com",
    )

    project = create_personal_project(
        client,
        token,
        title="Progress Personal Project",
    )
    project_id = project["project_id"]

    task_1 = create_personal_task(
        client,
        token,
        project_id,
        title="Completed Progress Task",
    )
    create_personal_task(
        client,
        token,
        project_id,
        title="Todo Progress Task",
    )

    update_response = client.patch(
        f"/projects/{project_id}/tasks/{task_1['task_id']}",
        headers=auth_headers(token),
        json={
            "status": "completed",
            "actual_hours": 2,
        },
    )

    assert update_response.status_code == 200, update_response.text

    response = client.get(
        f"/projects/{project_id}/progress",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["project"]["project_id"] == project_id
    assert data["project"]["total_tasks"] == 2
    assert data["project"]["completed_tasks"] == 1
    assert data["project"]["pending_tasks"] == 1
    assert data["project"]["completion_percentage"] == pytest.approx(50.0)
    assert data["task_status_counts"]["completed"] == 1
    assert data["task_status_counts"]["todo"] == 1
    assert data["current_user_progress"]["tasks_total"] == 2
    assert data["current_user_progress"]["tasks_completed"] == 1
    assert data["current_user_progress"]["completion_percentage"] == pytest.approx(50.0)
    assert len(data["recommendations"]) >= 1


def test_get_progress_blocks_cross_user_personal_project_access(
    client: TestClient,
    db: Session,
) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="progressprivateowner",
        email="progressprivateowner@example.com",
    )

    _other_id, other_token = create_verified_user_and_login(
        client,
        db,
        username="progressintruder",
        email="progressintruder@example.com",
    )

    project = create_personal_project(
        client,
        owner_token,
        title="Private Progress Project",
    )

    response = client.get(
        f"/projects/{project['project_id']}/progress",
        headers=auth_headers(other_token),
    )

    assert response.status_code == 404


def test_get_team_project_progress_for_owner_success(
    client: TestClient,
    db: Session,
) -> None:
    owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="progressteamowner",
        email="progressteamowner@example.com",
    )

    team = create_team(
        client,
        owner_token,
        name="Progress Team",
    )

    project = create_team_project(
        client,
        owner_token,
        team_id=team["team_id"],
        title="Team Progress Project",
    )

    task = create_team_task(
        client,
        owner_token,
        team_id=team["team_id"],
        project_id=project["project_id"],
        assigned_to=owner_id,
        title="Team Completed Progress Task",
    )

    update_response = client.patch(
        f"/teams/{team['team_id']}/projects/{project['project_id']}/tasks/{task['task_id']}",
        headers=auth_headers(owner_token),
        json={
            "status": "completed",
            "actual_hours": 3,
        },
    )

    assert update_response.status_code == 200, update_response.text

    response = client.get(
        f"/projects/{project['project_id']}/progress",
        headers=auth_headers(owner_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["project"]["project_type"] == "team"
    assert data["project"]["total_tasks"] == 1
    assert data["project"]["completed_tasks"] == 1
    assert data["project"]["completion_percentage"] == pytest.approx(100.0)
    assert data["current_user_progress"]["user_id"] == owner_id
    assert data["current_user_progress"]["completion_percentage"] == pytest.approx(100.0)
    assert len(data["members"]) >= 1


def test_get_progress_missing_token_returns_401(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username="progressnotoken",
        email="progressnotoken@example.com",
    )

    project = create_personal_project(
        client,
        token,
        title="No Token Progress Project",
    )

    response = client.get(f"/projects/{project['project_id']}/progress")

    assert response.status_code == 401
