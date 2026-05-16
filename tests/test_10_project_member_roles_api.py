from __future__ import annotations

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from tests.conftest import (
    auth_headers,
    create_team,
    create_team_project,
    create_verified_user_and_login,
)


def add_team_member(
    client: TestClient,
    token: str,
    team_id: int,
    email: str,
    role: str = "member",
) -> dict:
    response = client.post(
        f"/teams/{team_id}/members",
        headers=auth_headers(token),
        json={
            "email": email,
            "role": role,
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def test_project_owner_can_update_project_member_role(
    client: TestClient,
    db: Session,
) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="projectroleowner",
        email="projectroleowner@example.com",
    )

    member_id, _member_token = create_verified_user_and_login(
        client,
        db,
        username="projectrolemember",
        email="projectrolemember@example.com",
    )

    team = create_team(client, owner_token)
    team_id = team["team_id"]

    add_team_member(
        client=client,
        token=owner_token,
        team_id=team_id,
        email="projectrolemember@example.com",
        role="member",
    )

    project = create_team_project(client, owner_token, team_id)
    project_id = project["project_id"]

    response = client.patch(
        f"/teams/{team_id}/projects/{project_id}/members/{member_id}",
        headers=auth_headers(owner_token),
        json={"role": "manager"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["user_id"] == member_id
    assert response.json()["role"] == "manager"


def test_project_manager_cannot_update_project_member_role(
    client: TestClient,
    db: Session,
) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="projectroleowner2",
        email="projectroleowner2@example.com",
    )

    manager_id, manager_token = create_verified_user_and_login(
        client,
        db,
        username="projectrolemanager",
        email="projectrolemanager@example.com",
    )

    member_id, _member_token = create_verified_user_and_login(
        client,
        db,
        username="projectrolemember2",
        email="projectrolemember2@example.com",
    )

    team = create_team(client, owner_token)
    team_id = team["team_id"]

    add_team_member(
        client=client,
        token=owner_token,
        team_id=team_id,
        email="projectrolemanager@example.com",
        role="admin",
    )

    add_team_member(
        client=client,
        token=owner_token,
        team_id=team_id,
        email="projectrolemember2@example.com",
        role="member",
    )

    project = create_team_project(client, owner_token, team_id)
    project_id = project["project_id"]

    members_response = client.get(
        f"/teams/{team_id}/projects/{project_id}/members",
        headers=auth_headers(owner_token),
    )

    assert members_response.status_code == 200
    manager_project_member = next(
        member
        for member in members_response.json()
        if member["user_id"] == manager_id
    )
    assert manager_project_member["role"] == "manager"

    response = client.patch(
        f"/teams/{team_id}/projects/{project_id}/members/{member_id}",
        headers=auth_headers(manager_token),
        json={"role": "manager"},
    )

    assert response.status_code == 403


def test_project_owner_cannot_assign_owner_role(
    client: TestClient,
    db: Session,
) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="projectroleowner3",
        email="projectroleowner3@example.com",
    )

    member_id, _member_token = create_verified_user_and_login(
        client,
        db,
        username="projectrolemember3",
        email="projectrolemember3@example.com",
    )

    team = create_team(client, owner_token)
    team_id = team["team_id"]

    add_team_member(
        client=client,
        token=owner_token,
        team_id=team_id,
        email="projectrolemember3@example.com",
        role="member",
    )

    project = create_team_project(client, owner_token, team_id)
    project_id = project["project_id"]

    response = client.patch(
        f"/teams/{team_id}/projects/{project_id}/members/{member_id}",
        headers=auth_headers(owner_token),
        json={"role": "owner"},
    )

    assert response.status_code == 422


def test_project_owner_role_cannot_be_changed(
    client: TestClient,
    db: Session,
) -> None:
    owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="projectroleowner4",
        email="projectroleowner4@example.com",
    )

    team = create_team(client, owner_token)
    team_id = team["team_id"]

    project = create_team_project(client, owner_token, team_id)
    project_id = project["project_id"]

    response = client.patch(
        f"/teams/{team_id}/projects/{project_id}/members/{owner_id}",
        headers=auth_headers(owner_token),
        json={"role": "member"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Project owner role cannot be changed through this endpoint."
    )
