from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ai_plan import AIPlan
from app.models.project import Project
from app.models.task import Task

from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_team,
    create_team_project,
    create_verified_user_and_login,
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
    assert data["generated_plan"]["source"] == "local_rule_based_v1"
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


def test_generate_ai_plan_endpoint_uses_business_tasks_for_clothing_idea(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_clothing_owner",
        email="ai_generate_clothing_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Clothing Business Launch",
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plan/generate",
        headers=auth_headers(token),
        json={
            "prompt": (
                "I want to start a clothing business with a small online store, "
                "suppliers, delivery, branding, and legal setup."
            ),
            "generate_tasks": True,
            "overwrite_existing_tasks": False,
            "preferred_task_count": 8,
            "include_milestones": True,
        },
    )

    assert response.status_code == 201, response.text

    task_titles = " ".join(
        task["title"].lower()
        for task in response.json()["tasks"]
    )

    assert "supplier" in task_titles
    assert "brand" in task_titles
    assert "product collection" in task_titles
    assert "delivery" in task_titles
    assert "app" not in task_titles
    assert "software" not in task_titles
    assert "code" not in task_titles
    assert "land" not in task_titles
    assert "factory" not in task_titles


def test_generate_ai_plan_ignores_negative_instruction_text_for_clothing_business(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_clothing_social_owner",
        email="ai_generate_clothing_social_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Clothing business online",
    )

    response = client.post(
        f"/projects/{project['project_id']}/ai-plan/generate",
        headers=auth_headers(token),
        json={
            "prompt": "\n".join(
                [
                    "Create a complete Planora project plan and task list.",
                    "Project title: Clothing business online",
                    "Available hours per week: 8",
                    "Preferred task count: 10",
                    "",
                    "Project idea and goal:",
                    "I want to create my own page on social media and sell my clothing brand online",
                    "",
                    "Do not default to software, app, coding, or implementation tasks unless the idea is software.",
                ]
            ),
            "generate_tasks": True,
            "preferred_task_count": 10,
        },
    )

    assert response.status_code == 201, response.text

    tasks = response.json()["tasks"]
    task_titles = " ".join(task["title"].lower() for task in tasks)
    task_descriptions = "\n".join(
        (task["description"] or "")
        for task in tasks
    )

    assert "clothing niche" in task_titles
    assert "social media content" in task_titles
    assert "online sales channel" in task_titles
    assert "delivery, payment, and returns" in task_titles
    assert "design the app architecture" not in task_titles
    assert "build the core product features" not in task_titles
    assert "test key user flows" not in task_titles
    assert "Create a complete Planora project plan" not in task_descriptions
    assert "Available hours per week" not in task_descriptions
    assert "Preferred task count" not in task_descriptions
    assert "Do not default to software" not in task_descriptions


def test_generate_ai_plan_uses_software_tasks_for_explicit_flutter_app(
    client: TestClient,
    db: Session,
):
    _, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="ai_generate_software_owner",
        email="ai_generate_software_owner@example.com",
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

    task_titles = " ".join(
        task["title"].lower()
        for task in response.json()["tasks"]
    )

    assert "design the app architecture and data model" in task_titles
    assert "build the core product features" in task_titles


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
            "project_idea": "I want to create my own page on social media and sell my clothing brand online",
            "deadline": "2026-08-01T12:00:00+00:00",
            "project_type": "personal",
            "available_hours_per_week": 8,
            "preferred_task_count": 8,
            "requirements": "Start with a small collection and low budget.",
        },
    )

    assert preview_response.status_code == 200, preview_response.text
    assert db.query(Project).count() == before_count

    preview = preview_response.json()
    assert preview["domain"] == "business"
    assert any("clothing niche" in task["title"].lower() for task in preview["tasks"])

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
