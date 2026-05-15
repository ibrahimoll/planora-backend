from __future__ import annotations

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


def test_personal_task_comments_crud(client: TestClient, db: Session) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username="commentuser",
        email="commentuser@example.com",
    )

    project = create_personal_project(client, token)
    task = create_personal_task(client, token, project["project_id"])

    create_response = client.post(
        f"/projects/{project['project_id']}/tasks/{task['task_id']}/comments",
        headers=auth_headers(token),
        json={"comment_text": "First pytest comment"},
    )

    assert create_response.status_code == 201
    comment = create_response.json()
    assert comment["comment_text"] == "First pytest comment"

    update_response = client.patch(
        f"/projects/{project['project_id']}/tasks/{task['task_id']}/comments/{comment['comment_id']}",
        headers=auth_headers(token),
        json={"comment_text": "Updated pytest comment"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["comment_text"] == "Updated pytest comment"

    delete_response = client.delete(
        f"/projects/{project['project_id']}/tasks/{task['task_id']}/comments/{comment['comment_id']}",
        headers=auth_headers(token),
    )

    assert delete_response.status_code == 200


def test_team_comment_mention_creates_notification(
    client: TestClient,
    db: Session,
) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="mentionowner",
        email="mentionowner@example.com",
    )

    member_id, member_token = create_verified_user_and_login(
        client,
        db,
        username="mentionmember",
        email="mentionmember@example.com",
    )

    team = create_team(client, owner_token)

    add_member_response = client.post(
        f"/teams/{team['team_id']}/members",
        headers=auth_headers(owner_token),
        json={
            "email": "mentionmember@example.com",
            "role": "member",
        },
    )

    assert add_member_response.status_code == 201

    project = create_team_project(client, owner_token, team["team_id"])

    task = create_team_task(
        client,
        owner_token,
        team_id=team["team_id"],
        project_id=project["project_id"],
        assigned_to=member_id,
    )

    comment_response = client.post(
        f"/teams/{team['team_id']}/projects/{project['project_id']}/tasks/{task['task_id']}/comments",
        headers=auth_headers(owner_token),
        json={"comment_text": "Please check this @mentionmember"},
    )

    assert comment_response.status_code == 201

    notifications_response = client.get(
        "/notifications?unread_only=true",
        headers=auth_headers(member_token),
    )

    assert notifications_response.status_code == 200

    notifications = notifications_response.json()
    assert any(notification["type"] == "mention" for notification in notifications)


def test_notification_mark_read_and_count(client: TestClient, db: Session) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="notifowner",
        email="notifowner@example.com",
    )

    _member_id, member_token = create_verified_user_and_login(
        client,
        db,
        username="notifmember",
        email="notifmember@example.com",
    )

    team = create_team(client, owner_token)

    invite_response = client.post(
        f"/teams/{team['team_id']}/invitations",
        headers=auth_headers(owner_token),
        json={
            "username": "notifmember",
            "role": "member",
        },
    )

    assert invite_response.status_code == 201

    unread_count_response = client.get(
        "/notifications/unread-count",
        headers=auth_headers(member_token),
    )

    assert unread_count_response.status_code == 200
    assert unread_count_response.json()["unread_count"] >= 1

    notifications_response = client.get(
        "/notifications?unread_only=true",
        headers=auth_headers(member_token),
    )

    assert notifications_response.status_code == 200
    notification_id = notifications_response.json()[0]["notification_id"]

    mark_read_response = client.patch(
        f"/notifications/{notification_id}/read",
        headers=auth_headers(member_token),
    )

    assert mark_read_response.status_code == 200
    assert mark_read_response.json()["is_read"] is True
