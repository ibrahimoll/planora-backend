from __future__ import annotations

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from tests.conftest import (
    auth_headers,
    create_team,
    create_team_project,
    create_verified_user_and_login,
)


def test_team_invitation_accept_flow(client: TestClient, db: Session) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="inviteowner",
        email="inviteowner@example.com",
    )

    member_id, member_token = create_verified_user_and_login(
        client,
        db,
        username="invitemember",
        email="invitemember@example.com",
    )

    team = create_team(client, owner_token)
    project = create_team_project(client, owner_token, team["team_id"])

    invite_response = client.post(
        f"/teams/{team['team_id']}/invitations",
        headers=auth_headers(owner_token),
        json={
            "username": "invitemember",
            "role": "member",
        },
    )

    assert invite_response.status_code == 201
    invitation = invite_response.json()
    assert invitation["status"] == "pending"

    my_invites_response = client.get(
        "/invitations/me",
        headers=auth_headers(member_token),
    )

    assert my_invites_response.status_code == 200
    assert len(my_invites_response.json()) == 1

    accept_response = client.post(
        f"/invitations/{invitation['invitation_id']}/accept",
        headers=auth_headers(member_token),
    )

    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "accepted"

    team_members_response = client.get(
        f"/teams/{team['team_id']}/members",
        headers=auth_headers(owner_token),
    )

    assert team_members_response.status_code == 200
    assert any(member["user_id"] == member_id for member in team_members_response.json())

    project_members_response = client.get(
        f"/teams/{team['team_id']}/projects/{project['project_id']}/members",
        headers=auth_headers(owner_token),
    )

    assert project_members_response.status_code == 200
    assert any(member["user_id"] == member_id for member in project_members_response.json())


def test_team_invitation_reject_flow(client: TestClient, db: Session) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="rejectowner",
        email="rejectowner@example.com",
    )

    _member_id, member_token = create_verified_user_and_login(
        client,
        db,
        username="rejectmember",
        email="rejectmember@example.com",
    )

    team = create_team(client, owner_token)

    invite_response = client.post(
        f"/teams/{team['team_id']}/invitations",
        headers=auth_headers(owner_token),
        json={
            "username": "rejectmember",
            "role": "member",
        },
    )

    assert invite_response.status_code == 201
    invitation = invite_response.json()

    reject_response = client.post(
        f"/invitations/{invitation['invitation_id']}/reject",
        headers=auth_headers(member_token),
    )

    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"
