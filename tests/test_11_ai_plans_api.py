from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ai_plan import AIPlan
from app.models.project import Project
from app.models.task import Task
from app.schemas.ai_plan_schema import AIPlanPreviewRequest
from app.schemas.project_schema import ProjectType
from app.services.ai_plan_service import build_generated_plan, create_ai_plan_preview

from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_team,
    create_team_project,
    create_verified_user_and_login,
)


def _requested_task_count(prompt: str, default: int = 6) -> int:
    match = re.search(
        r"generate exactly\s+(\d+)\s+tasks?",
        prompt,
        flags=re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    match = re.search(r"preferred task count:\s*(\d+)", prompt, flags=re.IGNORECASE)

    if match:
        return int(match.group(1))

    return default


def _idea_focus(prompt: str) -> str:
    stopwords = {
        "planora",
        "project",
        "tasks",
        "task",
        "return",
        "json",
        "valid",
        "description",
        "deadline",
        "priority",
        "estimated",
        "hours",
        "generated",
        "generate",
        "exactly",
    }
    tokens = [
        token
        for token in re.findall(r"[A-Za-z][A-Za-z0-9'-]{3,}", prompt.lower())
        if token not in stopwords
    ]

    return " ".join(tokens[:3]) or "idea"


def _provider_task(index: int, focus: str) -> dict[str, object]:
    verbs = ["Define", "Map", "Create", "Test", "Review", "Schedule", "Track", "Share"]
    verb = verbs[(index - 1) % len(verbs)]
    title = f"{verb} {focus} checkpoint {index}"

    return {
        "suggested_order": index,
        "title": title,
        "description": _provider_description(title=title, index=index, focus=focus),
        "priority": "high" if index == 1 else "medium",
        "estimated_hours": 2,
    }


def _provider_description(*, title: str, index: int, focus: str) -> str:
    deliverables = [
        "decision checklist",
        "materials list",
        "practice schedule",
        "test notes",
        "feedback table",
        "progress tracker",
    ]
    deliverable = deliverables[(index - 1) % len(deliverables)]

    return (
        f"Goal: Complete '{title}' so the {focus} idea has a useful checkpoint {index}.\n\n"
        "Steps:\n"
        f"1. Review the {focus} context and choose the detail needed for '{title}'.\n"
        f"2. Write three concrete decisions that belong only to checkpoint {index}.\n"
        f"3. Create a {deliverable} that supports the next {focus} action.\n\n"
        f"Deliverable: A {focus} {deliverable} for '{title}'.\n\n"
        f"Done when: The {deliverable} has at least three concrete items tied to {focus}.\n\n"
        f"Why it matters: This keeps the original {focus} goal moving through '{title}'."
    )


def _provider_plan(prompt: str) -> str:
    task_count = _requested_task_count(prompt)
    focus = _idea_focus(prompt)

    return json.dumps(
        {
            "domain": "idea-driven",
            "summary": f"AI provider generated tasks for {focus}.",
            "tasks": [
                _provider_task(index=index, focus=focus)
                for index in range(1, task_count + 1)
            ],
            "milestones": [
                {
                    "name": f"{focus.title()} checkpoint",
                    "description": f"First useful checkpoint for {focus}.",
                    "suggested_order": 1,
                }
            ],
            "risks": [],
            "recommendations": [],
        }
    )


@pytest.fixture(autouse=True)
def mock_ai_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        _provider_plan,
    )


def test_generate_ai_plan_for_personal_project_creates_tasks(
    client: TestClient,
    db: Session,
):
    user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_owner",
        email="ai_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="AI Personal Project",
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plans",
        headers=auth_headers(token),
        json={
            "input_prompt": "Plan my final year project backend.",
            "create_tasks": True,
            "task_count": 4,
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["project_id"] == project["project_id"]
    assert data["generated_by"] == user_id
    assert data["input_prompt"] == "Plan my final year project backend."
    assert data["generated_plan"]["source"] == "ai_provider"
    assert data["generated_plan"]["success"] is True
    assert data["generated_plan"]["ai_generation_status"] == "generated"
    assert len(data["generated_plan"]["tasks"]) == 4
    assert len(data["generated_plan"]["created_task_ids"]) == 4

    tasks_response = client.get(
        f"/projects/{project['project_id']}/tasks",
        headers=auth_headers(token),
    )

    assert tasks_response.status_code == 200, tasks_response.text
    assert len(tasks_response.json()) == 4


def test_generate_ai_plan_without_task_creation_stores_plan_only(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_no_tasks",
        email="ai_no_tasks@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="AI Plan Only Project",
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plans",
        headers=auth_headers(token),
        json={
            "input_prompt": "Only generate the plan, do not create tasks.",
            "create_tasks": False,
            "task_count": 3,
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["generated_plan"]["source"] == "ai_provider"
    assert len(data["generated_plan"]["tasks"]) == 3
    assert data["generated_plan"]["created_task_ids"] == []

    tasks_response = client.get(
        f"/projects/{project['project_id']}/tasks",
        headers=auth_headers(token),
    )

    assert tasks_response.status_code == 200, tasks_response.text
    assert tasks_response.json() == []


def test_list_personal_project_ai_plans(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_list_owner",
        email="ai_list_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="AI List Project",
    )

    for prompt in ["First plan", "Second plan"]:
        response = client.post(
            f"/projects/{project['project_id']}/ai-plans",
            headers=auth_headers(token),
            json={
                "input_prompt": prompt,
                "create_tasks": False,
                "task_count": 3,
            },
        )

        assert response.status_code == 201, response.text

    list_response = client.get(
        f"/projects/{project['project_id']}/ai-plans",
        headers=auth_headers(token),
    )

    assert list_response.status_code == 200, list_response.text

    plans = list_response.json()

    assert len(plans) == 2
    assert plans[0]["project_id"] == project["project_id"]
    assert plans[1]["project_id"] == project["project_id"]


def test_cross_user_cannot_generate_ai_plan_for_personal_project(
    client: TestClient,
    db: Session,
):
    _, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_cross_owner",
        email="ai_cross_owner@example.com",
    )

    _, stranger_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_cross_stranger",
        email="ai_cross_stranger@example.com",
    )

    project = create_personal_project(
        client=client,
        token=owner_token,
        title="Private AI Project",
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plans",
        headers=auth_headers(stranger_token),
        json={
            "input_prompt": "Try to generate for another user's project.",
            "create_tasks": False,
            "task_count": 3,
        },
    )

    assert response.status_code == 404, response.text


def test_missing_token_cannot_generate_ai_plan(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_missing_token",
        email="ai_missing_token@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Missing Token AI Project",
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plans",
        json={
            "input_prompt": "No token request.",
            "create_tasks": False,
            "task_count": 3,
        },
    )

    assert response.status_code == 401, response.text


def test_team_project_owner_can_generate_ai_plan(
    client: TestClient,
    db: Session,
):
    owner_id, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_team_owner",
        email="ai_team_owner@example.com",
    )

    team = create_team(
        client=client,
        token=owner_token,
        name="AI Team",
    )

    project = create_team_project(
        client=client,
        token=owner_token,
        team_id=team["team_id"],
        title="AI Team Project",
    )

    response = client.post(
        f"/teams/{team['team_id']}/projects/{project['project_id']}/ai-plans",
        headers=auth_headers(owner_token),
        json={
            "input_prompt": "Generate a team project plan.",
            "create_tasks": True,
            "task_count": 3,
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["project_id"] == project["project_id"]
    assert data["generated_by"] == owner_id
    assert data["generated_plan"]["source"] == "ai_provider"
    assert len(data["generated_plan"]["created_task_ids"]) == 3


def test_team_project_member_cannot_generate_ai_plan(
    client: TestClient,
    db: Session,
):
    _, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_team_owner_2",
        email="ai_team_owner_2@example.com",
    )

    _, member_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_team_member",
        email="ai_team_member@example.com",
    )

    team = create_team(
        client=client,
        token=owner_token,
        name="AI Permission Team",
    )

    add_member_response = client.post(
        f"/teams/{team['team_id']}/members",
        headers=auth_headers(owner_token),
        json={
            "email": "ai_team_member@example.com",
            "role": "member",
        },
    )

    assert add_member_response.status_code == 201, add_member_response.text

    project = create_team_project(
        client=client,
        token=owner_token,
        team_id=team["team_id"],
        title="AI Permission Team Project",
    )

    response = client.post(
        f"/teams/{team['team_id']}/projects/{project['project_id']}/ai-plans",
        headers=auth_headers(member_token),
        json={
            "input_prompt": "Member should not generate.",
            "create_tasks": False,
            "task_count": 3,
        },
    )

    assert response.status_code == 403, response.text


def test_generate_ai_plan_endpoint_requires_auth(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_auth_owner",
        email="ai_generate_auth_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="AI Generate Auth Project",
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plan/generate",
        json={"prompt": "Generate without token."},
    )

    assert response.status_code == 401, response.text


def test_generate_ai_plan_endpoint_creates_plan_row_and_tasks(
    client: TestClient,
    db: Session,
):
    user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_owner",
        email="ai_generate_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Flutter AI Planning Project",
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plan/generate",
        headers=auth_headers(token),
        json={
            "prompt": "Create a Flutter mobile app with auth and tasks.",
            "generate_tasks": True,
            "overwrite_existing_tasks": False,
            "preferred_task_count": 8,
            "include_milestones": True,
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["project_id"] == project["project_id"]
    assert data["plan_id"]
    assert data["tasks_created"] == 8
    assert len(data["tasks"]) == 8
    assert data["summary"]

    ai_plan = db.get(AIPlan, data["plan_id"])
    assert ai_plan is not None
    assert ai_plan.project_id == project["project_id"]
    assert ai_plan.generated_by == user_id
    assert ai_plan.input_prompt == "Create a Flutter mobile app with auth and tasks."
    assert ai_plan.generated_plan["created_task_ids"]
    assert ai_plan.generated_plan["milestones"]

    project_deadline = datetime.fromisoformat(project["deadline"])

    for task_data in data["tasks"]:
        assert task_data["priority"] in {"low", "medium", "high"}
        assert task_data["status"] == "todo"
        assert task_data["estimated_hours"] is None or task_data["estimated_hours"] >= 0
        assert datetime.fromisoformat(task_data["due_date"]) <= project_deadline

    tasks_response = client.get(
        f"/projects/{project['project_id']}/tasks",
        headers=auth_headers(token),
    )

    assert tasks_response.status_code == 200, tasks_response.text

    tasks = tasks_response.json()

    assert len(tasks) == 8
    assert {task["assigned_to"] for task in tasks} == {user_id}


def test_generate_ai_plan_endpoint_uses_provider_tasks_for_user_idea(
    client: TestClient,
    db: Session,
    monkeypatch,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_provider_owner",
        email="ai_generate_provider_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Backyard Telescope Night",
    )

    provider_titles = [
        "Map backyard telescope viewing constraints",
        "Create moon and planet observation checklist",
        "Schedule family skywatching practice night",
    ]

    def provider_reply(_prompt: str) -> str:
        return json.dumps(
            {
                "domain": "astronomy hobby",
                "summary": "Provider-specific skywatching plan.",
                "tasks": [
                    {
                        **_provider_task(index=index, focus="backyard telescope"),
                        "title": title,
                    }
                    for index, title in enumerate(provider_titles, start=1)
                ],
                "milestones": [],
                "risks": [],
                "recommendations": [],
            }
        )

    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        provider_reply,
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plan/generate",
        headers=auth_headers(token),
        json={
            "prompt": (
                "Plan a backyard telescope night where my family can observe "
                "the moon and two planets before bedtime."
            ),
            "generate_tasks": True,
            "overwrite_existing_tasks": False,
            "preferred_task_count": 3,
            "include_milestones": True,
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()
    assert data["success"] is True
    assert data["ai_generation_status"] == "generated"
    assert [task["title"] for task in data["tasks"]] == provider_titles


def test_generate_ai_plan_ignores_prompt_instruction_text_when_validating_tasks(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_instruction_owner",
        email="ai_generate_instruction_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Community Repair Circle",
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plan/generate",
        headers=auth_headers(token),
        json={
            "prompt": "\n".join(
                [
                    "Create a complete Planora project plan and task list.",
                    "Project title: Community repair circle",
                    "Available hours per week: 8",
                    "Preferred task count: 10",
                    "",
                    "Project idea and goal:",
                    "I want to organize a monthly repair circle where neighbors fix small household items together",
                    "",
                    "Return valid JSON and avoid unrelated boilerplate.",
                ]
            ),
            "generate_tasks": True,
            "preferred_task_count": 4,
        },
    )

    assert response.status_code == 201, response.text

    tasks = response.json()["tasks"]
    task_descriptions = "\n".join(
        (task["description"] or "")
        for task in tasks
    )

    assert "Create a complete Planora project plan" not in task_descriptions
    assert "Available hours per week" not in task_descriptions
    assert "Preferred task count" not in task_descriptions
    assert "Return valid JSON" not in task_descriptions
    assert len(tasks) == 4


def test_generate_ai_plan_uses_provider_tasks_for_app_idea(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_app_owner",
        email="ai_generate_app_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Food Delivery Product",
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plan/generate",
        headers=auth_headers(token),
        json={
            "prompt": "Build a Flutter mobile app for food delivery.",
            "generate_tasks": True,
            "preferred_task_count": 6,
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()
    assert data["success"] is True
    assert data["ai_generation_status"] == "generated"
    assert data["tasks_created"] == 6
    assert len({task["title"] for task in data["tasks"]}) == 6


def test_generate_ai_plan_provider_unavailable_returns_failed_without_fake_tasks(
    client: TestClient,
    db: Session,
    monkeypatch,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_outage_owner",
        email="ai_generate_outage_owner@example.com",
    )

    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        lambda _prompt: None,
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Quiet Weekend Reading Plan",
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plan/generate",
        headers=auth_headers(token),
        json={
            "prompt": "Create a quiet weekend reading plan with notes and reflection time.",
            "generate_tasks": True,
            "preferred_task_count": 6,
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()
    assert data["success"] is False
    assert data["ai_generation_status"] == "failed"
    assert data["message"] == "AI planning is unavailable right now. Please try again."
    assert data["tasks_created"] == 0
    assert data["tasks"] == []


def test_preview_from_idea_does_not_create_project_until_accepted(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_preview_owner",
        email="ai_preview_owner@example.com",
    )

    before_count = db.query(Project).count()
    preview_response = client.post(
        "/ai-plans/preview-from-idea",
        headers=auth_headers(token),
        json={
            "project_idea": "I want to organize a tiny living-room concert for neighbors using only borrowed instruments",
            "deadline": "2026-08-01T12:00:00+00:00",
            "project_type": "personal",
            "available_hours_per_week": 8,
            "preferred_task_count": 8,
            "requirements": "Keep it quiet, friendly, and easy to set up.",
        },
    )

    assert preview_response.status_code == 200, preview_response.text
    assert db.query(Project).count() == before_count

    preview = preview_response.json()
    assert preview["success"] is True
    assert preview["source"] == "ai_provider"
    assert len(preview["tasks"]) == 8

    accept_response = client.post(
        "/ai-plans/accept-preview",
        headers=auth_headers(token),
        json={"preview": preview},
    )

    assert accept_response.status_code == 201, accept_response.text

    accepted = accept_response.json()
    assert accepted["project"]["project_id"] == accepted["project_id"]
    assert accepted["tasks_created"] == 8
    assert db.query(Project).count() == before_count + 1


def test_preview_from_idea_returns_success_with_provider_json(
    client: TestClient,
    db: Session,
    monkeypatch,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_preview_provider_json_owner",
        email="ai_preview_provider_json_owner@example.com",
    )

    provider_titles = [
        "Define compost workshop audience needs",
        "Map compost workshop material checklist",
        "Create compost workshop practice agenda",
    ]

    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        lambda _prompt: _provider_plan_from_titles(
            titles=provider_titles,
            focus="compost workshop",
        ),
    )

    response = client.post(
        "/ai-plans/preview-from-idea",
        headers=auth_headers(token),
        json={
            "project_idea": "Plan a neighborhood compost workshop for apartment residents with limited kitchen space",
            "deadline": "2026-08-01T12:00:00+00:00",
            "project_type": "personal",
            "available_hours_per_week": 6,
            "preferred_task_count": 3,
            "requirements": "Keep the workshop beginner friendly and low cost.",
        },
    )

    assert response.status_code == 200, response.text

    preview = response.json()
    assert preview["success"] is True
    assert preview["ai_generation_status"] == "generated"
    assert preview["source"] == "ai_provider"
    assert preview["project_title"]
    assert preview["description"]
    assert preview["summary"]
    assert [task["title"] for task in preview["tasks"]] == provider_titles
    assert preview["ai_generation_status"] != "failed"


def test_preview_from_idea_falls_back_when_provider_returns_none(
    client: TestClient,
    db: Session,
    monkeypatch,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_preview_provider_none_owner",
        email="ai_preview_provider_none_owner@example.com",
    )

    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        lambda _prompt: None,
    )

    response = client.post(
        "/ai-plans/preview-from-idea",
        headers=auth_headers(token),
        json={
            "project_idea": "Create a launch checklist for a small handmade candle subscription box",
            "deadline": "2026-08-01T12:00:00+00:00",
            "project_type": "personal",
            "available_hours_per_week": 5,
            "preferred_task_count": 4,
            "requirements": "Include packaging, pricing, and the first customer test.",
        },
    )

    assert response.status_code == 200, response.text

    preview = response.json()
    assert preview["success"] is True
    assert preview["ai_generation_status"] == "fallback"
    assert preview["source"] in {
        "local_planner_fallback_v1",
        "minimum_local_planner_v1",
    }
    assert preview["tasks"]
    assert len(preview["tasks"]) == 4
    assert preview["ai_generation_status"] != "failed"

    for task in preview["tasks"]:
        assert task["title"]
        assert task["description"]
        assert task["priority"] in {"low", "medium", "high"}
        assert task["estimated_hours"] is not None


def test_preview_from_idea_parses_markdown_fenced_json(
    client: TestClient,
    db: Session,
    monkeypatch,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_preview_fenced_json_owner",
        email="ai_preview_fenced_json_owner@example.com",
    )

    provider_titles = [
        "Define herb garden shelf constraints",
        "Create herb garden supply checklist",
        "Test herb garden watering routine",
    ]
    provider_json = _provider_plan_from_titles(
        titles=provider_titles,
        focus="herb garden",
    )

    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        lambda _prompt: f"```json\n{provider_json}\n```",
    )

    response = client.post(
        "/ai-plans/preview-from-idea",
        headers=auth_headers(token),
        json={
            "project_idea": "Build a tiny indoor herb garden plan for a sunny kitchen shelf",
            "deadline": "2026-08-01T12:00:00+00:00",
            "project_type": "personal",
            "available_hours_per_week": 4,
            "preferred_task_count": 3,
        },
    )

    assert response.status_code == 200, response.text

    preview = response.json()
    assert preview["success"] is True
    assert preview["ai_generation_status"] == "generated"
    assert [task["title"] for task in preview["tasks"]] == provider_titles
    assert preview["ai_generation_status"] != "failed"


def test_generate_ai_plan_endpoint_can_store_plan_without_creating_tasks(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_no_tasks",
        email="ai_generate_no_tasks@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="AI Generate Plan Only Project",
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plan/generate",
        headers=auth_headers(token),
        json={
            "prompt": "Store a plan only.",
            "generate_tasks": False,
            "preferred_task_count": 5,
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["tasks_created"] == 0
    assert data["tasks"] == []
    assert db.get(AIPlan, data["plan_id"]) is not None

    tasks_response = client.get(
        f"/projects/{project['project_id']}/tasks",
        headers=auth_headers(token),
    )

    assert tasks_response.status_code == 200, tasks_response.text
    assert tasks_response.json() == []


def test_generate_ai_plan_endpoint_does_not_overwrite_existing_tasks_by_default(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_append",
        email="ai_generate_append@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="AI Append Project",
    )
    existing_task = create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Keep this task",
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plan/generate",
        headers=auth_headers(token),
        json={
            "prompt": "Append generated tasks.",
            "generate_tasks": True,
            "overwrite_existing_tasks": False,
            "preferred_task_count": 3,
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["tasks_created"] == 3
    assert db.get(Task, existing_task["task_id"]) is not None

    tasks_response = client.get(
        f"/projects/{project['project_id']}/tasks",
        headers=auth_headers(token),
    )

    assert tasks_response.status_code == 200, tasks_response.text
    assert len(tasks_response.json()) == 4


def test_generate_ai_plan_endpoint_skips_duplicate_existing_tasks(
    client: TestClient,
    db: Session,
    monkeypatch,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_duplicate_skip",
        email="ai_generate_duplicate_skip@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="AI Duplicate Prevention",
    )
    existing_task = create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Define launch checklist",
    )

    def fake_generated_plan(**kwargs):
        return {
            "source": "test",
            "domain": "general",
            "summary": "Added only missing work.",
            "tasks": [
                {
                    "suggested_order": 1,
                    "title": "Define launch checklist",
                    "description": "Duplicate exact title.",
                    "priority": "medium",
                    "estimated_hours": 1,
                    "due_date": project["deadline"],
                },
                {
                    "suggested_order": 2,
                    "title": "Define the launch checklist",
                    "description": "Duplicate similar title.",
                    "priority": "medium",
                    "estimated_hours": 1,
                    "due_date": project["deadline"],
                },
                {
                    "suggested_order": 3,
                    "title": "Validate launch schedule",
                    "description": "A genuinely complementary task.",
                    "priority": "high",
                    "estimated_hours": 2,
                    "due_date": project["deadline"],
                },
            ],
            "milestones": [],
            "risks": [],
            "recommendations": [],
        }

    monkeypatch.setattr(
        "app.services.ai_plan_service.build_generated_plan",
        fake_generated_plan,
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plan/generate",
        headers=auth_headers(token),
        json={
            "prompt": "Improve this plan without duplicate tasks.",
            "generate_tasks": True,
            "overwrite_existing_tasks": False,
            "preferred_task_count": 3,
        },
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["tasks_created"] == 1
    assert data["tasks_skipped_as_duplicates"] == 2
    assert data["improvement_summary"] == "Added only missing work."
    assert data["tasks"][0]["title"] == "Validate launch schedule"
    assert db.get(Task, existing_task["task_id"]) is not None

    tasks_response = client.get(
        f"/projects/{project['project_id']}/tasks",
        headers=auth_headers(token),
    )

    assert tasks_response.status_code == 200, tasks_response.text
    assert sorted(task["title"] for task in tasks_response.json()) == [
        "Define launch checklist",
        "Validate launch schedule",
    ]


def test_team_project_member_can_generate_ai_plan_endpoint(
    client: TestClient,
    db: Session,
):
    owner_id, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_team_owner",
        email="ai_generate_team_owner@example.com",
    )
    member_id, member_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_team_member",
        email="ai_generate_team_member@example.com",
    )

    team = create_team(
        client=client,
        token=owner_token,
        name="AI Generate Member Team",
    )

    add_member_response = client.post(
        f"/teams/{team['team_id']}/members",
        headers=auth_headers(owner_token),
        json={
            "email": "ai_generate_team_member@example.com",
            "role": "member",
        },
    )

    assert add_member_response.status_code == 201, add_member_response.text

    project = create_team_project(
        client=client,
        token=owner_token,
        team_id=team["team_id"],
        title="AI Generate Team Project",
    )

    response = client.post(
        f"/teams/{team['team_id']}/projects/{project['project_id']}/ai-plan/generate",
        headers=auth_headers(member_token),
        json={
            "prompt": "Generate team project tasks.",
            "generate_tasks": True,
            "preferred_task_count": 4,
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["tasks_created"] == 4

    tasks_response = client.get(
        f"/teams/{team['team_id']}/projects/{project['project_id']}/tasks",
        headers=auth_headers(member_token),
    )

    assert tasks_response.status_code == 200, tasks_response.text

    assigned_user_ids = {
        task["assigned_to"]
        for task in tasks_response.json()
        if task["assigned_to"] is not None
    }

    assert assigned_user_ids <= {owner_id, member_id}
    assert assigned_user_ids


def test_non_member_cannot_generate_team_ai_plan_endpoint(
    client: TestClient,
    db: Session,
):
    _, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_forbidden_owner",
        email="ai_generate_forbidden_owner@example.com",
    )
    _, stranger_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_forbidden_stranger",
        email="ai_generate_forbidden_stranger@example.com",
    )

    team = create_team(
        client=client,
        token=owner_token,
        name="AI Generate Forbidden Team",
    )
    project = create_team_project(
        client=client,
        token=owner_token,
        team_id=team["team_id"],
        title="AI Generate Forbidden Project",
    )

    response = client.post(
        f"/teams/{team['team_id']}/projects/{project['project_id']}/ai-plan/generate",
        headers=auth_headers(stranger_token),
        json={
            "prompt": "Try to generate tasks.",
            "generate_tasks": False,
        },
    )

    assert response.status_code == 403, response.text


SMART_SECTIONS = (
    "Goal:",
    "Steps:",
    "Deliverable:",
    "Done when:",
    "Why it matters:",
)


def _quality_project(idea: str) -> Project:
    return Project(
        project_id=0,
        created_by=1,
        team_id=None,
        title=idea[:80],
        description=idea,
        deadline=datetime.now(timezone.utc) + timedelta(days=14),
        status="not_started",
        project_type="personal",
    )


def _provider_plan_from_titles(
    *,
    titles: list[str],
    focus: str,
    domain: str = "idea-driven",
    message: str | None = None,
) -> str:
    return json.dumps(
        {
            "domain": domain,
            "summary": f"Provider plan for {focus}.",
            "message": message or "Generated AI tasks from the user idea.",
            "tasks": [
                _provider_task_with_title(index=index, focus=focus, title=title)
                for index, title in enumerate(titles, start=1)
            ],
            "milestones": [],
            "risks": [],
            "recommendations": [],
        }
    )


def _provider_task_with_title(
    *,
    index: int,
    focus: str,
    title: str,
) -> dict[str, object]:
    return {
        **_provider_task(index=index, focus=focus),
        "title": title,
        "description": _provider_description(title=title, index=index, focus=focus),
    }


def _assert_provider_generated_tasks(
    plan: dict,
    *,
    expected_count: int,
) -> None:
    tasks = plan["tasks"]

    assert len(tasks) == expected_count
    assert len({task["title"] for task in tasks}) == expected_count
    assert len({task["description"] for task in tasks}) == expected_count

    due_dates = [
        datetime.fromisoformat(task["due_date"])
        for task in tasks
    ]
    assert due_dates == sorted(due_dates)

    for task in tasks:
        description = task["description"]

        assert task["priority"] in {"low", "medium", "high"}
        assert 0.5 <= float(task["estimated_hours"]) <= 12

        for section in SMART_SECTIONS:
            assert section in description

        assert len(re.findall(r"(?:^|\n)\s*\d+\.", description)) >= 3
        assert "return JSON" not in description
        assert "Project context:" not in description
        assert "Preferred task count" not in description


class _PreviewUser:
    user_id = 1


def _pushup_preview_request(task_count: int = 8) -> AIPlanPreviewRequest:
    return AIPlanPreviewRequest(
        project_idea="Do 100 pushup a day",
        deadline=datetime.now(timezone.utc) + timedelta(days=30),
        project_type=ProjectType.personal,
        available_hours_per_week=5,
        preferred_task_count=task_count,
    )


def _assert_no_forbidden_planner_language(text: str) -> None:
    lowered = text.lower()

    for forbidden in (
        "features",
        "requirements",
        "mvp",
        "first useful version",
        "customer benefit",
        "idea goal",
    ):
        assert forbidden not in lowered


def test_pushup_preview_fallback_returns_fitness_specific_tasks(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        lambda _prompt: None,
    )

    preview = create_ai_plan_preview(_pushup_preview_request(), _PreviewUser())

    titles = [task.title for task in preview.tasks]
    all_text = " ".join(
        [preview.summary, *titles, *(task.description or "" for task in preview.tasks)]
    )

    assert preview.success is True
    assert preview.ai_generation_status == "fallback"
    assert preview.domain == "fitness_health"
    assert titles == [
        "Test your current max pushups",
        "Set a safe daily starting volume",
        "Split pushups into manageable sets",
        "Practice correct pushup form",
        "Create a 2-week progression schedule",
        "Add recovery and pain rules",
        "Track reps, sets, and difficulty",
        "Review progress after 14 days",
    ]
    assert len(preview.tasks) == 8
    assert "8 tasks" in preview.summary
    _assert_no_forbidden_planner_language(all_text)


def test_pushup_preview_summary_count_matches_tasks_length(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        lambda _prompt: None,
    )

    preview = create_ai_plan_preview(_pushup_preview_request(task_count=8), _PreviewUser())
    match = re.search(r"\b(\d+)\s+tasks?\b", preview.summary)

    assert match is not None
    assert int(match.group(1)) == len(preview.tasks)


def test_pushup_preview_malformed_provider_json_uses_domain_fallback(monkeypatch):
    calls: list[str] = []

    def malformed_provider(prompt: str) -> str:
        calls.append(prompt)
        return "not json"

    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        malformed_provider,
    )

    preview = create_ai_plan_preview(_pushup_preview_request(), _PreviewUser())
    all_text = " ".join(
        [preview.summary, *(task.description or "" for task in preview.tasks)]
    )

    assert len(calls) == 2
    assert preview.ai_generation_status == "fallback"
    assert len(preview.tasks) == 8
    assert preview.tasks[0].title == "Test your current max pushups"
    _assert_no_forbidden_planner_language(all_text)


def test_preview_uses_provider_json_when_available(monkeypatch):
    provider_titles = [
        "Define task tracker core user flow",
        "Prioritize task tracker first-release features",
        "Create task tracker test checklist",
    ]

    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        lambda _prompt: _provider_plan_from_titles(
            titles=provider_titles,
            focus="task tracker app",
            domain="software_app",
        ),
    )

    preview = create_ai_plan_preview(
        AIPlanPreviewRequest(
            project_idea="Build a task tracker app for daily chores",
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
            project_type=ProjectType.personal,
            preferred_task_count=3,
        ),
        _PreviewUser(),
    )

    assert preview.ai_generation_status == "generated"
    assert preview.source == "ai_provider"
    assert [task.title for task in preview.tasks] == provider_titles


@pytest.mark.parametrize(
    ("idea", "focus", "provider_titles"),
    [
        (
            "Build a paper umbrella repair kit for rainy market days",
            "paper umbrella",
            [
                "Map paper umbrella repair failure points",
                "Create paper umbrella patch kit checklist",
                "Test paper umbrella repair steps in light rain",
            ],
        ),
        (
            "Plan a silent piano practice routine for an apartment with thin walls",
            "silent piano",
            [
                "Define silent piano practice limits",
                "Schedule silent piano finger-drill sessions",
                "Track silent piano progress without noise",
            ],
        ),
        (
            "Create a shared balcony seed library for three neighbors",
            "balcony seed",
            [
                "List balcony seed sharing rules",
                "Create balcony seed packet tracker",
                "Review balcony seed swap feedback",
            ],
        ),
    ],
)
def test_ai_provider_specific_unusual_ideas_pass_without_templates(
    monkeypatch,
    idea: str,
    focus: str,
    provider_titles: list[str],
):
    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        lambda _prompt: _provider_plan_from_titles(
            titles=provider_titles,
            focus=focus,
        ),
    )

    plan = build_generated_plan(
        project=_quality_project(idea),
        input_prompt=idea,
        task_count=3,
        include_milestones=True,
    )

    assert plan["success"] is True
    assert plan["source"] == "ai_provider"
    assert plan["ai_generation_status"] == "generated"
    assert [task["title"] for task in plan["tasks"]] == provider_titles
    _assert_provider_generated_tasks(plan, expected_count=3)


def test_ai_provider_unrelated_json_is_rejected_without_fake_tasks(monkeypatch):
    idea = "Plan a silent piano practice routine for an apartment with thin walls"
    calls: list[str] = []

    def provider_reply(prompt: str) -> str | None:
        calls.append(prompt)

        if len(calls) == 1:
            return _provider_plan_from_titles(
                titles=[
                    "Map submarine coral archive checkpoint",
                    "Create submarine coral archive checklist",
                    "Review submarine coral archive notes",
                ],
                focus="submarine coral archive",
            )

        return None

    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        provider_reply,
    )

    plan = build_generated_plan(
        project=_quality_project(idea),
        input_prompt=idea,
        task_count=3,
        include_milestones=False,
    )

    assert len(calls) == 2
    assert plan["success"] is False
    assert plan["ai_generation_status"] == "failed"
    assert plan["tasks"] == []
    assert plan["rejected_unrelated_count"] >= 3


def test_ai_provider_invalid_json_gets_one_repair_call(monkeypatch):
    idea = "Build a paper umbrella repair kit for rainy market days"
    calls: list[str] = []

    def provider_reply(prompt: str) -> str:
        calls.append(prompt)

        if len(calls) == 1:
            return "not valid json"

        return _provider_plan_from_titles(
            titles=[
                "Map paper umbrella repair failure points",
                "Create paper umbrella repair checklist",
                "Test paper umbrella repair kit",
            ],
            focus="paper umbrella",
        )

    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        provider_reply,
    )

    plan = build_generated_plan(
        project=_quality_project(idea),
        input_prompt=idea,
        task_count=3,
        include_milestones=False,
    )

    assert len(calls) == 2
    assert "Repair this into valid JSON" in calls[1]
    assert plan["success"] is True
    assert plan["ai_generation_status"] == "repaired"
    _assert_provider_generated_tasks(plan, expected_count=3)


def test_provider_unavailable_returns_failed_plan_without_local_tasks(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        lambda _prompt: None,
    )

    plan = build_generated_plan(
        project=_quality_project("Create a shared balcony seed library"),
        input_prompt="Create a shared balcony seed library",
        task_count=4,
        include_milestones=True,
    )

    assert plan["success"] is False
    assert plan["ai_generation_status"] == "failed"
    assert plan["message"] == "AI planning is unavailable right now. Please try again."
    assert plan["tasks"] == []
    assert plan["milestones"] == []


def test_improve_plan_rejects_existing_task_duplicates(monkeypatch):
    idea = "Plan a silent piano practice routine for an apartment with thin walls"
    existing_description = _provider_task(index=1, focus="silent piano")["description"]
    existing_task = Task(
        project_id=0,
        created_by=1,
        title="Define silent piano practice limits",
        description=str(existing_description),
        priority="medium",
        estimated_hours=1,
        status="todo",
    )
    calls: list[str] = []

    def provider_reply(prompt: str) -> str:
        calls.append(prompt)

        if len(calls) == 1:
            return _provider_plan_from_titles(
                titles=[
                    "Define silent piano practice limits",
                    "Schedule silent piano finger-drill sessions",
                    "Track silent piano progress without noise",
                ],
                focus="silent piano",
            )

        return _provider_plan_from_titles(
            titles=["Review silent piano weekly adjustment notes"],
            focus="silent piano",
        )

    monkeypatch.setattr(
        "app.services.ai_plan_service.generate_ai_reply_from_provider",
        provider_reply,
    )

    plan = build_generated_plan(
        project=_quality_project(idea),
        input_prompt=idea,
        task_count=3,
        include_milestones=False,
        existing_tasks=[existing_task],
    )

    titles = [task["title"] for task in plan["tasks"]]
    assert len(calls) == 2
    assert plan["success"] is True
    assert "Define silent piano practice limits" not in titles
    assert len(titles) == 3
    assert plan["rejected_generic_count"] >= 1


def test_preview_from_idea_rejects_too_short_input(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_preview_short_input_owner",
        email="ai_preview_short_input_owner@example.com",
    )

    response = client.post(
        "/ai-plans/preview-from-idea",
        headers=auth_headers(token),
        json={
            "project_idea": "Too short",
            "deadline": "2026-08-01T12:00:00+00:00",
            "project_type": "personal",
            "available_hours_per_week": 8,
            "preferred_task_count": 6,
        },
    )

    assert response.status_code == 422, response.text
