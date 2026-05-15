from __future__ import annotations

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from tests.conftest import (
    auth_headers,
    create_team,
    create_team_project,
    create_team_task,
    create_verified_user_and_login,
)


def test_team_crud_and_owner_membership(client: TestClient, db: Session) -> None:
    user_id, token = create_verified_user_and_login(
        client,
        db,
        username="teamowner",
        email="teamowner@example.com",
    )

    team = create_team(client, token)
    team_id = team["team_id"]

    assert team["name"] == "Pytest Team"
    assert team["created_by"] == user_id

    list_response = client.get(
        "/teams",
        headers=auth_headers(token),
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    members_response = client.get(
        f"/teams/{team_id}/members",
        headers=auth_headers(token),
    )

    assert members_response.status_code == 200
    members = members_response.json()
    assert len(members) == 1
    assert members[0]["user_id"] == user_id
    assert members[0]["role"] == "owner"


def test_team_project_and_task_flow(client: TestClient, db: Session) -> None:
    owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="teamprojectowner",
        email="teamprojectowner@example.com",
    )

    team = create_team(client, owner_token)
    team_id = team["team_id"]

    project = create_team_project(client, owner_token, team_id)
    project_id = project["project_id"]

    assert project["project_type"] == "team"
    assert project["team_id"] == team_id

    task = create_team_task(
        client,
        owner_token,
        team_id=team_id,
        project_id=project_id,
        assigned_to=owner_id,
    )

    assert task["project_id"] == project_id
    assert task["assigned_to"] == owner_id

    update_response = client.patch(
        f"/teams/{team_id}/projects/{project_id}/tasks/{task['task_id']}",
        headers=auth_headers(owner_token),
        json={
            "status": "in_progress",
            "actual_hours": 1,
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "in_progress"


def test_team_owner_can_add_member_by_email(client: TestClient, db: Session) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="addmemberowner",
        email="addmemberowner@example.com",
    )

    member_id, _member_token = create_verified_user_and_login(
        client,
        db,
        username="addmemberuser",
        email="addmemberuser@example.com",
    )

    team = create_team(client, owner_token)

    response = client.post(
        f"/teams/{team['team_id']}/members",
        headers=auth_headers(owner_token),
        json={
            "email": "addmemberuser@example.com",
            "role": "member",
        },
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == member_id
    assert response.json()["role"] == "member"


def test_owner_can_update_team_member_role(client: TestClient, db: Session) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="roleowner",
        email="roleowner@example.com",
    )

    member_id, _member_token = create_verified_user_and_login(
        client,
        db,
        username="rolemember",
        email="rolemember@example.com",
    )

    team = create_team(client, owner_token)

    add_response = client.post(
        f"/teams/{team['team_id']}/members",
        headers=auth_headers(owner_token),
        json={
            "email": "rolemember@example.com",
            "role": "member",
        },
    )

    assert add_response.status_code == 201

    update_response = client.patch(
        f"/teams/{team['team_id']}/members/{member_id}",
        headers=auth_headers(owner_token),
        json={"role": "admin"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["role"] == "admin"
