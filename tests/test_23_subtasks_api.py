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


def test_personal_subtask_crud_updates_task_progress(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client,
        db,
        username="subtaskowner",
        email="subtaskowner@example.com",
    )
    project = create_personal_project(client, token, title="Checklist project")
    task = create_personal_task(
        client,
        token,
        project_id=project["project_id"],
        title="Checklist task",
    )
    path = f"/projects/{project['project_id']}/tasks/{task['task_id']}"

    first_response = client.post(
        f"{path}/subtasks",
        headers=auth_headers(token),
        json={"title": "Draft the outline"},
    )
    second_response = client.post(
        f"{path}/subtasks",
        headers=auth_headers(token),
        json={"title": "Review the outline"},
    )

    assert first_response.status_code == 201, first_response.text
    assert second_response.status_code == 201, second_response.text
    first = first_response.json()
    second = second_response.json()
    assert first["status"] == "todo"
    assert first["is_completed"] is False

    empty_response = client.post(
        f"{path}/subtasks",
        headers=auth_headers(token),
        json={"title": "   "},
    )
    assert empty_response.status_code == 422

    list_response = client.get(f"{path}/subtasks", headers=auth_headers(token))
    assert list_response.status_code == 200
    assert [item["title"] for item in list_response.json()] == [
        "Draft the outline",
        "Review the outline",
    ]

    update_response = client.patch(
        f"{path}/subtasks/{first['subtask_id']}",
        headers=auth_headers(token),
        json={"title": "Draft and share the outline"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Draft and share the outline"

    complete_response = client.patch(
        f"{path}/subtasks/{first['subtask_id']}/complete",
        headers=auth_headers(token),
        json={"is_completed": True},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"
    assert complete_response.json()["completed_at"] is not None

    detail_response = client.get(path, headers=auth_headers(token))
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["subtask_count"] == 2
    assert detail["completed_subtask_count"] == 1
    assert detail["progress_percentage"] == pytest.approx(50.0)
    assert len(detail["subtasks"]) == 2

    client.patch(
        f"{path}/subtasks/{second['subtask_id']}/complete",
        headers=auth_headers(token),
        json={"is_completed": True},
    )
    completed_detail = client.get(path, headers=auth_headers(token)).json()
    assert completed_detail["progress_percentage"] == pytest.approx(100.0)
    assert completed_detail["status"] == "todo"

    uncomplete_response = client.patch(
        f"{path}/subtasks/{first['subtask_id']}/complete",
        headers=auth_headers(token),
        json={"is_completed": False},
    )
    assert uncomplete_response.status_code == 200
    assert uncomplete_response.json()["status"] == "todo"
    assert uncomplete_response.json()["completed_at"] is None
    assert client.get(path, headers=auth_headers(token)).json()[
        "progress_percentage"
    ] == pytest.approx(50.0)

    delete_response = client.delete(
        f"{path}/subtasks/{first['subtask_id']}",
        headers=auth_headers(token),
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Subtask deleted successfully."
    assert [item["subtask_id"] for item in client.get(
        f"{path}/subtasks", headers=auth_headers(token)
    ).json()] == [second["subtask_id"]]


def test_personal_subtasks_block_other_users(
    client: TestClient,
    db: Session,
) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="privatechecklistowner",
        email="privatechecklistowner@example.com",
    )
    _other_id, other_token = create_verified_user_and_login(
        client,
        db,
        username="privatechecklistother",
        email="privatechecklistother@example.com",
    )
    project = create_personal_project(client, owner_token)
    task = create_personal_task(client, owner_token, project["project_id"])
    path = f"/projects/{project['project_id']}/tasks/{task['task_id']}/subtasks"

    assert client.get(path, headers=auth_headers(other_token)).status_code == 404
    assert client.post(
        path,
        headers=auth_headers(other_token),
        json={"title": "Not allowed"},
    ).status_code == 404


def test_team_assignee_can_manage_subtasks_but_other_members_are_read_only(
    client: TestClient,
    db: Session,
) -> None:
    owner_id, owner_token = create_verified_user_and_login(
        client,
        db,
        username="teamsubtaskowner",
        email="teamsubtaskowner@example.com",
    )
    assignee_id, assignee_token = create_verified_user_and_login(
        client,
        db,
        username="teamsubtaskassignee",
        email="teamsubtaskassignee@example.com",
    )
    _viewer_id, viewer_token = create_verified_user_and_login(
        client,
        db,
        username="teamsubtaskviewer",
        email="teamsubtaskviewer@example.com",
    )
    _stranger_id, stranger_token = create_verified_user_and_login(
        client,
        db,
        username="teamsubtaskstranger",
        email="teamsubtaskstranger@example.com",
    )
    team = create_team(client, owner_token, name="Checklist team")

    for email in (
        "teamsubtaskassignee@example.com",
        "teamsubtaskviewer@example.com",
    ):
        response = client.post(
            f"/teams/{team['team_id']}/members",
            headers=auth_headers(owner_token),
            json={"email": email, "role": "member"},
        )
        assert response.status_code == 201, response.text

    project = create_team_project(client, owner_token, team["team_id"])
    task = create_team_task(
        client,
        owner_token,
        team_id=team["team_id"],
        project_id=project["project_id"],
        assigned_to=assignee_id,
    )
    path = (
        f"/teams/{team['team_id']}/projects/{project['project_id']}"
        f"/tasks/{task['task_id']}/subtasks"
    )

    created_response = client.post(
        path,
        headers=auth_headers(assignee_token),
        json={"title": "Assignee checklist item"},
    )
    assert created_response.status_code == 201, created_response.text
    subtask_id = created_response.json()["subtask_id"]

    viewer_list = client.get(path, headers=auth_headers(viewer_token))
    assert viewer_list.status_code == 200
    assert len(viewer_list.json()) == 1
    assert client.post(
        path,
        headers=auth_headers(viewer_token),
        json={"title": "Viewer cannot add"},
    ).status_code == 403

    update_response = client.patch(
        f"{path}/{subtask_id}",
        headers=auth_headers(assignee_token),
        json={"title": "Updated by assignee"},
    )
    assert update_response.status_code == 200
    complete_response = client.patch(
        f"{path}/{subtask_id}/complete",
        headers=auth_headers(assignee_token),
        json={"is_completed": True},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["is_completed"] is True

    assert client.get(path, headers=auth_headers(stranger_token)).status_code == 403
    assert client.delete(
        f"{path}/{subtask_id}", headers=auth_headers(owner_token)
    ).status_code == 200
    assert owner_id == task["created_by"]
