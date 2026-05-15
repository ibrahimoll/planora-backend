from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_verified_user_and_login,
)


def test_project_owner_can_list_activity_logs(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_owner",
        email="activity_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Activity Timeline Project",
    )

    task = create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Activity Timeline Task",
    )

    response = client.get(
        f"/projects/{project['project_id']}/activity",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    data = response.json()
    event_types = [item["event_type"] for item in data]

    assert "project_created" in event_types
    assert "task_created" in event_types

    task_log = next(
        item for item in data
        if item["event_type"] == "task_created"
    )

    assert task_log["project_id"] == project["project_id"]
    assert task_log["task_id"] == task["task_id"]
    assert task_log["task_title_snapshot"] == "Activity Timeline Task"
    assert task_log["actor_username_snapshot"] == "activity_owner"
    assert task_log["message"]
    assert task_log["created_at"]


def test_activity_logs_are_ordered_newest_first(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_order_owner",
        email="activity_order_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Activity Order Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="First Activity Task",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Second Activity Task",
    )

    response = client.get(
        f"/projects/{project['project_id']}/activity",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    data = response.json()
    activity_ids = [item["activity_id"] for item in data]

    assert activity_ids == sorted(activity_ids, reverse=True)


def test_activity_logs_can_be_filtered_by_event_type(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_filter_owner",
        email="activity_filter_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Filtered Activity Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Filtered Activity Task",
    )

    response = client.get(
        f"/projects/{project['project_id']}/activity?event_type=task_created",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert len(data) >= 1
    assert all(item["event_type"] == "task_created" for item in data)


def test_activity_logs_support_limit_and_offset(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_paging_owner",
        email="activity_paging_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Activity Paging Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Paging Task One",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Paging Task Two",
    )

    first_page_response = client.get(
        f"/projects/{project['project_id']}/activity?limit=1&offset=0",
        headers=auth_headers(token),
    )

    second_page_response = client.get(
        f"/projects/{project['project_id']}/activity?limit=1&offset=1",
        headers=auth_headers(token),
    )

    assert first_page_response.status_code == 200, first_page_response.text
    assert second_page_response.status_code == 200, second_page_response.text

    first_page = first_page_response.json()
    second_page = second_page_response.json()

    assert len(first_page) == 1
    assert len(second_page) == 1
    assert first_page[0]["activity_id"] != second_page[0]["activity_id"]


def test_user_cannot_list_other_users_personal_project_activity(
    client: TestClient,
    db: Session,
):
    _owner_id, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_private_owner",
        email="activity_private_owner@example.com",
    )

    _other_id, other_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_private_other",
        email="activity_private_other@example.com",
    )

    project = create_personal_project(
        client=client,
        token=owner_token,
        title="Private Activity Project",
    )

    response = client.get(
        f"/projects/{project['project_id']}/activity",
        headers=auth_headers(other_token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_unauthenticated_user_cannot_list_activity_logs(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_auth_owner",
        email="activity_auth_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Auth Activity Project",
    )

    response = client.get(
        f"/projects/{project['project_id']}/activity",
    )

    assert response.status_code == 401
