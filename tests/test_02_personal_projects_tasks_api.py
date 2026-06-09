from __future__ import annotations

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.models.project import Project
from app.models.task import Task

from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_verified_user_and_login,
)


def test_personal_project_crud(client: TestClient, db: Session) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username="projectuser",
        email="projectuser@example.com",
    )

    project = create_personal_project(client, token)
    project_id = project["project_id"]

    assert project["title"] == "Personal Project Test"
    assert project["project_type"] == "personal"

    list_response = client.get(
        "/projects",
        headers=auth_headers(token),
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = client.get(
        f"/projects/{project_id}",
        headers=auth_headers(token),
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["project_id"] == project_id

    update_response = client.patch(
        f"/projects/{project_id}",
        headers=auth_headers(token),
        json={
            "title": "Updated Personal Project",
            "status": "in_progress",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Personal Project"
    assert update_response.json()["status"] == "in_progress"

    delete_response = client.delete(
        f"/projects/{project_id}",
        headers=auth_headers(token),
    )

    assert delete_response.status_code == 200


def test_personal_task_crud(client: TestClient, db: Session) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username="taskuser",
        email="taskuser@example.com",
    )

    project = create_personal_project(client, token)
    project_id = project["project_id"]

    task = create_personal_task(client, token, project_id)
    task_id = task["task_id"]

    assert task["status"] == "todo"
    assert task["priority"] == "medium"

    list_response = client.get(
        f"/projects/{project_id}/tasks",
        headers=auth_headers(token),
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.patch(
        f"/projects/{project_id}/tasks/{task_id}",
        headers=auth_headers(token),
        json={
            "status": "completed",
            "actual_hours": 2,
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "completed"
    assert update_response.json()["completed_at"] is not None

    delete_response = client.delete(
        f"/projects/{project_id}/tasks/{task_id}",
        headers=auth_headers(token),
    )

    assert delete_response.status_code == 200


def test_user_cannot_access_other_users_personal_project(
    client: TestClient,
    db: Session,
) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="ownerpersonal",
        email="ownerpersonal@example.com",
    )

    _other_id, other_token = create_verified_user_and_login(
        client,
        db,
        username="otherpersonal",
        email="otherpersonal@example.com",
    )

    project = create_personal_project(client, owner_token)

    response = client.get(
        f"/projects/{project['project_id']}",
        headers=auth_headers(other_token),
    )

    assert response.status_code == 404


def test_owner_invites_personal_project_collaborator(
    client: TestClient,
    db: Session,
) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="personalcollabowner",
        email="personalcollabowner@example.com",
    )

    member_id, member_token = create_verified_user_and_login(
        client,
        db,
        username="personalcollabmember",
        email="personalcollabmember@example.com",
    )

    _stranger_id, stranger_token = create_verified_user_and_login(
        client,
        db,
        username="personalcollabstranger",
        email="personalcollabstranger@example.com",
    )

    project = create_personal_project(
        client,
        owner_token,
        title="Shared Personal Project",
    )
    task = create_personal_task(
        client,
        owner_token,
        project_id=project["project_id"],
        title="Shared task",
    )

    invite_response = client.post(
        f"/projects/{project['project_id']}/members/invite",
        headers=auth_headers(owner_token),
        json={
            "email_or_username": "personalcollabmember@example.com",
            "role": "member",
        },
    )

    assert invite_response.status_code == 201, invite_response.text
    assert invite_response.json()["user_id"] == member_id

    duplicate_response = client.post(
        f"/projects/{project['project_id']}/members/invite",
        headers=auth_headers(owner_token),
        json={
            "email_or_username": "personalcollabmember@example.com",
            "role": "member",
        },
    )

    assert duplicate_response.status_code == 409

    member_projects_response = client.get(
        "/projects",
        headers=auth_headers(member_token),
    )

    assert member_projects_response.status_code == 200
    assert any(
        item["project_id"] == project["project_id"]
        for item in member_projects_response.json()
    )

    member_tasks_response = client.get(
        f"/projects/{project['project_id']}/tasks",
        headers=auth_headers(member_token),
    )

    assert member_tasks_response.status_code == 200
    assert [item["task_id"] for item in member_tasks_response.json()] == [
        task["task_id"]
    ]

    forbidden_delete_response = client.delete(
        f"/projects/{project['project_id']}",
        headers=auth_headers(member_token),
    )

    assert forbidden_delete_response.status_code == 404

    stranger_response = client.get(
        f"/projects/{project['project_id']}",
        headers=auth_headers(stranger_token),
    )

    assert stranger_response.status_code == 404

    owner_delete_response = client.delete(
        f"/projects/{project['project_id']}",
        headers=auth_headers(owner_token),
    )

    assert owner_delete_response.status_code == 200
    assert db.get(Project, project["project_id"]) is None


def test_deleting_personal_project_cascades_tasks(
    client: TestClient,
    db: Session,
) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="projectcascadeowner",
        email="projectcascadeowner@example.com",
    )

    project = create_personal_project(
        client,
        owner_token,
        title="Cascade Project",
    )
    task = create_personal_task(
        client,
        owner_token,
        project_id=project["project_id"],
        title="Delete with project",
    )

    delete_response = client.delete(
        f"/projects/{project['project_id']}",
        headers=auth_headers(owner_token),
    )

    assert delete_response.status_code == 200, delete_response.text
    assert db.get(Project, project["project_id"]) is None
    assert db.get(Task, task["task_id"]) is None
