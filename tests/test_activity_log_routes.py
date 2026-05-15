from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.team_member import TeamMember
from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_team,
    create_team_project,
    create_verified_user_and_login,
)


def get_activity(
    client: TestClient,
    token: str,
    project_id: int,
    query: str = "",
) -> list[dict]:
    response = client.get(
        f"/projects/{project_id}/activity{query}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text
    return response.json()


def get_event(
    activity_logs: list[dict],
    event_type: str,
) -> dict:
    return next(
        item for item in activity_logs
        if item["event_type"] == event_type
    )


def get_event_types(activity_logs: list[dict]) -> list[str]:
    return [item["event_type"] for item in activity_logs]


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

    activity_logs = get_activity(
        client=client,
        token=token,
        project_id=project["project_id"],
    )

    event_types = get_event_types(activity_logs)

    assert "project_created" in event_types
    assert "task_created" in event_types

    task_log = get_event(activity_logs, "task_created")

    assert task_log["project_id"] == project["project_id"]
    assert task_log["task_id"] == task["task_id"]
    assert task_log["task_title_snapshot"] == "Activity Timeline Task"
    assert task_log["actor_username_snapshot"] == "activity_owner"
    assert task_log["message"]
    assert task_log["created_at"]


def test_project_updated_activity_log_is_created(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_project_update_owner",
        email="activity_project_update_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Project Before Update",
    )

    response = client.patch(
        f"/projects/{project['project_id']}",
        headers=auth_headers(token),
        json={
            "title": "Project After Update",
            "status": "in_progress",
        },
    )

    assert response.status_code == 200, response.text

    activity_logs = get_activity(
        client=client,
        token=token,
        project_id=project["project_id"],
    )

    project_updated_log = get_event(activity_logs, "project_updated")

    assert project_updated_log["project_id"] == project["project_id"]
    assert project_updated_log["actor_username_snapshot"] == "activity_project_update_owner"
    assert "changed_fields" in project_updated_log["metadata"]
    assert "title" in project_updated_log["metadata"]["changed_fields"]
    assert "status" in project_updated_log["metadata"]["changed_fields"]


def test_task_updated_and_task_completed_activity_logs_are_created(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_task_update_owner",
        email="activity_task_update_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Task Update Activity Project",
    )

    task = create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Task Before Update",
    )

    update_response = client.patch(
        f"/projects/{project['project_id']}/tasks/{task['task_id']}",
        headers=auth_headers(token),
        json={
            "title": "Task After Update",
            "priority": "high",
            "status": "in_progress",
        },
    )

    assert update_response.status_code == 200, update_response.text

    complete_response = client.patch(
        f"/projects/{project['project_id']}/tasks/{task['task_id']}",
        headers=auth_headers(token),
        json={"status": "completed"},
    )

    assert complete_response.status_code == 200, complete_response.text

    activity_logs = get_activity(
        client=client,
        token=token,
        project_id=project["project_id"],
    )

    event_types = get_event_types(activity_logs)

    assert "task_updated" in event_types
    assert "task_completed" in event_types

    task_updated_log = get_event(activity_logs, "task_updated")
    task_completed_log = get_event(activity_logs, "task_completed")

    assert task_updated_log["task_id"] == task["task_id"]
    assert "priority" in task_updated_log["metadata"]["changed_fields"]
    assert task_completed_log["metadata"]["previous_status"] == "in_progress"
    assert task_completed_log["metadata"]["new_status"] == "completed"


def test_task_deleted_activity_log_is_created_and_snapshot_is_preserved(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_task_delete_owner",
        email="activity_task_delete_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Task Delete Activity Project",
    )

    task = create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Task To Delete",
    )

    delete_response = client.delete(
        f"/projects/{project['project_id']}/tasks/{task['task_id']}",
        headers=auth_headers(token),
    )

    assert delete_response.status_code == 200, delete_response.text

    activity_logs = get_activity(
        client=client,
        token=token,
        project_id=project["project_id"],
    )

    task_deleted_log = get_event(activity_logs, "task_deleted")

    assert task_deleted_log["project_id"] == project["project_id"]
    assert task_deleted_log["task_title_snapshot"] == "Task To Delete"
    assert task_deleted_log["metadata"]["task_id"] == task["task_id"]
    assert task_deleted_log["metadata"]["task_title"] == "Task To Delete"


def test_comment_created_updated_and_deleted_activity_logs_are_created(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_comment_owner",
        email="activity_comment_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Comment Activity Project",
    )

    task = create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Comment Activity Task",
    )

    create_response = client.post(
        f"/projects/{project['project_id']}/tasks/{task['task_id']}/comments",
        headers=auth_headers(token),
        json={"comment_text": "Initial activity comment"},
    )

    assert create_response.status_code == 201, create_response.text
    comment = create_response.json()

    update_response = client.patch(
        f"/projects/{project['project_id']}/tasks/{task['task_id']}/comments/{comment['comment_id']}",
        headers=auth_headers(token),
        json={"comment_text": "Updated activity comment"},
    )

    assert update_response.status_code == 200, update_response.text

    delete_response = client.delete(
        f"/projects/{project['project_id']}/tasks/{task['task_id']}/comments/{comment['comment_id']}",
        headers=auth_headers(token),
    )

    assert delete_response.status_code == 200, delete_response.text

    activity_logs = get_activity(
        client=client,
        token=token,
        project_id=project["project_id"],
    )

    event_types = get_event_types(activity_logs)

    assert "comment_created" in event_types
    assert "comment_updated" in event_types
    assert "comment_deleted" in event_types

    comment_created_log = get_event(activity_logs, "comment_created")
    comment_updated_log = get_event(activity_logs, "comment_updated")
    comment_deleted_log = get_event(activity_logs, "comment_deleted")

    assert comment_created_log["metadata"]["comment_id"] == comment["comment_id"]
    assert comment_updated_log["metadata"]["comment_id"] == comment["comment_id"]
    assert comment_deleted_log["metadata"]["comment_id"] == comment["comment_id"]


def test_attachment_uploaded_and_deleted_activity_logs_are_created(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_attachment_owner",
        email="activity_attachment_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Attachment Activity Project",
    )

    upload_response = client.post(
        f"/projects/{project['project_id']}/attachments",
        headers=auth_headers(token),
        files={
            "file": (
                "activity-file.txt",
                b"Activity attachment test content",
                "text/plain",
            ),
        },
    )

    assert upload_response.status_code == 201, upload_response.text
    attachment = upload_response.json()

    delete_response = client.delete(
        f"/projects/{project['project_id']}/attachments/{attachment['attachment_id']}",
        headers=auth_headers(token),
    )

    assert delete_response.status_code == 200, delete_response.text

    activity_logs = get_activity(
        client=client,
        token=token,
        project_id=project["project_id"],
    )

    event_types = get_event_types(activity_logs)

    assert "attachment_uploaded" in event_types
    assert "attachment_deleted" in event_types

    uploaded_log = get_event(activity_logs, "attachment_uploaded")
    deleted_log = get_event(activity_logs, "attachment_deleted")

    assert uploaded_log["metadata"]["attachment_id"] == attachment["attachment_id"]
    assert uploaded_log["metadata"]["file_name"] == "activity-file.txt"
    assert deleted_log["metadata"]["attachment_id"] == attachment["attachment_id"]
    assert deleted_log["metadata"]["file_name"] == "activity-file.txt"


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

    activity_logs = get_activity(
        client=client,
        token=token,
        project_id=project["project_id"],
    )

    activity_ids = [item["activity_id"] for item in activity_logs]

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

    activity_logs = get_activity(
        client=client,
        token=token,
        project_id=project["project_id"],
        query="?event_type=task_created",
    )

    assert len(activity_logs) >= 1
    assert all(item["event_type"] == "task_created" for item in activity_logs)


def test_invalid_activity_event_type_returns_422(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_invalid_event_owner",
        email="activity_invalid_event_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Invalid Event Activity Project",
    )

    response = client.get(
        f"/projects/{project['project_id']}/activity?event_type=bad_event",
        headers=auth_headers(token),
    )

    assert response.status_code == 422


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

    first_page = get_activity(
        client=client,
        token=token,
        project_id=project["project_id"],
        query="?limit=1&offset=0",
    )

    second_page = get_activity(
        client=client,
        token=token,
        project_id=project["project_id"],
        query="?limit=1&offset=1",
    )

    assert len(first_page) == 1
    assert len(second_page) == 1
    assert first_page[0]["activity_id"] != second_page[0]["activity_id"]


def test_invalid_activity_limit_and_offset_return_422(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_invalid_paging_owner",
        email="activity_invalid_paging_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Invalid Paging Activity Project",
    )

    bad_limit_low = client.get(
        f"/projects/{project['project_id']}/activity?limit=0",
        headers=auth_headers(token),
    )

    bad_limit_high = client.get(
        f"/projects/{project['project_id']}/activity?limit=101",
        headers=auth_headers(token),
    )

    bad_offset = client.get(
        f"/projects/{project['project_id']}/activity?offset=-1",
        headers=auth_headers(token),
    )

    assert bad_limit_low.status_code == 422
    assert bad_limit_high.status_code == 422
    assert bad_offset.status_code == 422


def test_activity_from_one_project_does_not_leak_into_another_project(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_isolation_owner",
        email="activity_isolation_owner@example.com",
    )

    first_project = create_personal_project(
        client=client,
        token=token,
        title="First Isolation Activity Project",
    )

    second_project = create_personal_project(
        client=client,
        token=token,
        title="Second Isolation Activity Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=first_project["project_id"],
        title="First Project Only Task",
    )

    second_project_logs = get_activity(
        client=client,
        token=token,
        project_id=second_project["project_id"],
    )

    assert all(
        item["project_id"] == second_project["project_id"]
        for item in second_project_logs
    )
    assert all(
        item["task_title_snapshot"] != "First Project Only Task"
        for item in second_project_logs
    )


def test_activity_endpoint_returns_empty_list_when_project_has_no_logs(
    client: TestClient,
    db: Session,
):
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_empty_owner",
        email="activity_empty_owner@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Empty Activity Project",
    )

    db.query(ActivityLog).filter(
        ActivityLog.project_id == project["project_id"],
    ).delete()
    db.commit()

    activity_logs = get_activity(
        client=client,
        token=token,
        project_id=project["project_id"],
    )

    assert activity_logs == []


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


def test_team_project_member_can_list_activity_logs_and_non_member_cannot(
    client: TestClient,
    db: Session,
):
    owner_id, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_team_owner",
        email="activity_team_owner@example.com",
    )

    member_id, member_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_team_member",
        email="activity_team_member@example.com",
    )

    _non_member_id, non_member_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="activity_team_non_member",
        email="activity_team_non_member@example.com",
    )

    team = create_team(
        client=client,
        token=owner_token,
        name="Activity Team",
    )

    db.add(
        TeamMember(
            team_id=team["team_id"],
            user_id=member_id,
            role="member",
        )
    )
    db.commit()

    project = create_team_project(
        client=client,
        token=owner_token,
        team_id=team["team_id"],
        title="Activity Team Project",
    )

    owner_activity = get_activity(
        client=client,
        token=owner_token,
        project_id=project["project_id"],
    )

    member_activity = get_activity(
        client=client,
        token=member_token,
        project_id=project["project_id"],
    )

    non_member_response = client.get(
        f"/projects/{project['project_id']}/activity",
        headers=auth_headers(non_member_token),
    )

    assert owner_activity
    assert member_activity
    assert get_event(owner_activity, "project_created")
    assert non_member_response.status_code == 404
    assert non_member_response.json()["detail"] == "Project not found"
    assert owner_id != member_id


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
