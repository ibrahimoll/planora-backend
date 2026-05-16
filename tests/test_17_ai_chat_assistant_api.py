from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.project_member import ProjectMember
from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_team,
    create_team_project,
    create_team_task,
    create_verified_user_and_login,
)


def test_personal_project_ai_chat_creates_user_and_ai_messages(
    client: TestClient,
    db: Session,
) -> None:
    user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="chat_owner",
        email="chat_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="AI Chat Personal Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Prepare requirements",
    )

    response = client.post(
        f"/projects/{project['project_id']}/chat",
        headers=auth_headers(token),
        json={"message": "What should I do next?"},
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["user_message"]["sender_type"] == "user"
    assert data["user_message"]["user_id"] == user_id
    assert data["user_message"]["message"] == "What should I do next?"

    assert data["ai_message"]["sender_type"] == "ai"
    assert data["ai_message"]["user_id"] is None
    assert "AI Chat Personal Project" in data["ai_message"]["message"]

    saved_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.project_id == project["project_id"])
        .order_by(ChatMessage.message_id.asc())
        .all()
    )

    assert len(saved_messages) == 2
    assert saved_messages[0].sender_type == "user"
    assert saved_messages[1].sender_type == "ai"


def test_personal_project_ai_chat_history_returns_saved_messages(
    client: TestClient,
    db: Session,
) -> None:
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="chat_history_owner",
        email="chat_history_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="AI Chat History Project",
    )

    response = client.post(
        f"/projects/{project['project_id']}/chat",
        headers=auth_headers(token),
        json={"message": "Give me a progress summary"},
    )

    assert response.status_code == 201, response.text

    history_response = client.get(
        f"/projects/{project['project_id']}/chat",
        headers=auth_headers(token),
    )

    assert history_response.status_code == 200, history_response.text

    data = history_response.json()

    assert len(data["messages"]) == 2
    assert data["messages"][0]["sender_type"] == "user"
    assert data["messages"][1]["sender_type"] == "ai"


def test_personal_project_ai_chat_excludes_other_users_projects(
    client: TestClient,
    db: Session,
) -> None:
    _, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="chat_real_owner",
        email="chat_real_owner@example.com",
    )

    _, other_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="chat_other_user",
        email="chat_other_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=owner_token,
        title="Private Chat Project",
    )

    response = client.post(
        f"/projects/{project['project_id']}/chat",
        headers=auth_headers(other_token),
        json={"message": "Can I access this?"},
    )

    assert response.status_code == 404, response.text


def test_team_project_member_can_use_ai_chat(
    client: TestClient,
    db: Session,
) -> None:
    owner_id, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="team_chat_owner",
        email="team_chat_owner@example.com",
    )

    member_id, member_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="team_chat_member",
        email="team_chat_member@example.com",
    )

    team = create_team(
        client=client,
        token=owner_token,
        name="AI Chat Team",
    )

    project = create_team_project(
        client=client,
        token=owner_token,
        team_id=team["team_id"],
        title="AI Chat Team Project",
    )

    db.add(
        ProjectMember(
            project_id=project["project_id"],
            user_id=member_id,
            role="member",
        )
    )
    db.commit()

    create_team_task(
        client=client,
        token=owner_token,
        team_id=team["team_id"],
        project_id=project["project_id"],
        assigned_to=member_id,
        title="Team chat task",
    )

    response = client.post(
        f"/teams/{team['team_id']}/projects/{project['project_id']}/chat",
        headers=auth_headers(member_token),
        json={"message": "Give me the project status"},
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["user_message"]["user_id"] == member_id
    assert data["ai_message"]["sender_type"] == "ai"
    assert "AI Chat Team Project" in data["ai_message"]["message"]


def test_team_project_non_member_cannot_use_ai_chat(
    client: TestClient,
    db: Session,
) -> None:
    _, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="team_chat_owner_forbidden",
        email="team_chat_owner_forbidden@example.com",
    )

    _, outsider_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="team_chat_outsider",
        email="team_chat_outsider@example.com",
    )

    team = create_team(
        client=client,
        token=owner_token,
        name="Forbidden Chat Team",
    )

    project = create_team_project(
        client=client,
        token=owner_token,
        team_id=team["team_id"],
        title="Forbidden Team Chat Project",
    )

    response = client.post(
        f"/teams/{team['team_id']}/projects/{project['project_id']}/chat",
        headers=auth_headers(outsider_token),
        json={"message": "Can I chat here?"},
    )

    assert response.status_code == 403, response.text


def test_ai_chat_requires_authentication(
    client: TestClient,
    db: Session,
) -> None:
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="chat_auth_owner",
        email="chat_auth_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Chat Auth Project",
    )

    response = client.post(
        f"/projects/{project['project_id']}/chat",
        json={"message": "No token"},
    )

    assert response.status_code == 401, response.text
