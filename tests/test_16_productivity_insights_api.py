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


def test_get_my_productivity_insights_for_personal_project_success(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username="insightsowner",
        email="insightsowner@example.com",
    )

    project = create_personal_project(
        client,
        token,
        title="Insights Personal Project",
    )

    task = create_personal_task(
        client,
        token,
        project["project_id"],
        title="Insights Completed Task",
    )
    create_personal_task(
        client,
        token,
        project["project_id"],
        title="Insights Todo Task",
    )

    update_response = client.patch(
        f"/projects/{project['project_id']}/tasks/{task['task_id']}",
        headers=auth_headers(token),
        json={
            "status": "completed",
            "actual_hours": 2,
        },
    )

    assert update_response.status_code == 200, update_response.text

    response = client.get(
        "/insights/me",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["summary"]["total_projects"] == 1
    assert data["summary"]["total_tasks"] == 2
    assert data["summary"]["assigned_tasks"] == 2
    assert data["summary"]["completed_assigned_tasks"] == 1
    assert data["summary"]["completion_percentage"] == pytest.approx(50.0)
    assert data["workload"]["assigned_incomplete_tasks"] == 1
    assert len(data["projects"]) == 1
    assert data["projects"][0]["title"] == "Insights Personal Project"
    assert data["projects"][0]["completion_percentage"] == pytest.approx(50.0)
    assert len(data["recommendations"]) >= 1


def test_get_my_productivity_insights_excludes_other_users_personal_projects(
    client: TestClient,
    db: Session,
) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="insightsprivateowner",
        email="insightsprivateowner@example.com",
    )
    _other_id, other_token = create_verified_user_and_login(
        client,
        db,
        username="insightsotheruser",
        email="insightsotheruser@example.com",
    )

    private_project = create_personal_project(
        client,
        owner_token,
        title="Private Project Should Not Appear",
    )
    create_personal_task(
        client,
        owner_token,
        private_project["project_id"],
        title="Private Task Should Not Appear",
    )

    visible_project = create_personal_project(
        client,
        other_token,
        title="Visible Other User Project",
    )
    create_personal_task(
        client,
        other_token,
        visible_project["project_id"],
        title="Visible Other User Task",
    )

    response = client.get(
        "/insights/me",
        headers=auth_headers(other_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()
    project_titles = [project["title"] for project in data["projects"]]

    assert "Visible Other User Project" in project_titles
    assert "Private Project Should Not Appear" not in project_titles
    assert data["summary"]["total_projects"] == 1


def test_get_my_productivity_insights_includes_team_project_for_member(
    client: TestClient,
    db: Session,
) -> None:
    owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="insightsteamowner",
        email="insightsteamowner@example.com",
    )

    team = create_team(
        client,
        owner_token,
        name="Insights Team",
    )
    project = create_team_project(
        client,
        owner_token,
        team_id=team["team_id"],
        title="Insights Team Project",
    )
    create_team_task(
        client,
        owner_token,
        team_id=team["team_id"],
        project_id=project["project_id"],
        assigned_to=owner_id,
        title="Insights High Priority Team Task",
    )

    response = client.get(
        "/insights/me",
        headers=auth_headers(owner_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()
    project_titles = [project_item["title"] for project_item in data["projects"]]

    assert "Insights Team Project" in project_titles
    assert data["summary"]["total_projects"] == 1
    assert data["summary"]["assigned_tasks"] == 1
    assert data["workload"]["high_priority_open_tasks"] == 1


def test_get_my_productivity_insights_missing_token_returns_401(
    client: TestClient,
    db: Session,
) -> None:
    response = client.get("/insights/me")

    assert response.status_code == 401
