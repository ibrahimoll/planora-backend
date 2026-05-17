from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_verified_user_and_login,
)


def test_ai_chat_uses_real_provider_when_provider_returns_reply(
    client: TestClient,
    db: Session,
    monkeypatch,
) -> None:
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="real_ai_chat_owner",
        email="real_ai_chat_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Real AI Chat Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Build real AI provider",
    )

    def fake_provider(prompt: str) -> str:
        assert "Real AI Chat Project" in prompt
        assert "Build real AI provider" in prompt
        assert "hello how are you" in prompt.lower()

        return "Hello! I am Planora AI. I checked your project and I can help you plan the next steps."

    monkeypatch.setattr(
        "app.services.ai_chat_service.generate_ai_reply_from_provider",
        fake_provider,
    )

    response = client.post(
        f"/projects/{project['project_id']}/chat",
        headers=auth_headers(token),
        json={"message": "hello how are you"},
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["ai_message"]["message"] == (
        "Hello! I am Planora AI. I checked your project and I can help you plan the next steps."
    )
    assert data["assistant_context"]["source"] == "gemini_llm_v1"
    assert data["assistant_context"]["fallback_used"] is False
    assert data["assistant_context"]["provider"] == "gemini"


def test_ai_chat_falls_back_to_local_reply_when_provider_returns_none(
    client: TestClient,
    db: Session,
    monkeypatch,
) -> None:
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="fallback_ai_chat_owner",
        email="fallback_ai_chat_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Fallback AI Chat Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Fallback task",
    )

    monkeypatch.setattr(
        "app.services.ai_chat_service.generate_ai_reply_from_provider",
        lambda prompt: None,
    )

    response = client.post(
        f"/projects/{project['project_id']}/chat",
        headers=auth_headers(token),
        json={"message": "What should I do next?"},
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["assistant_context"]["source"] == "local_rule_based_chat_v1"
    assert data["assistant_context"]["fallback_used"] is True
    assert "Fallback AI Chat Project" in data["ai_message"]["message"]
    assert "Fallback task" in data["ai_message"]["message"]
