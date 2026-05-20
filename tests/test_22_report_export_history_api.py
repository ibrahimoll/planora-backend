from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import (
    auth_headers,
    create_personal_project,
    create_personal_task,
    create_verified_user_and_login,
    make_admin_directly,
)


def test_export_project_report_creates_history_row(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="report_export_user",
        email="report_export_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Report Export History Project",
    )

    create_personal_task(
        client=client,
        token=token,
        project_id=project["project_id"],
        title="Task included in export history",
    )

    export_response = client.get(
        f"/reports/projects/{project['project_id']}",
        headers=auth_headers(token),
    )

    assert export_response.status_code == 200, export_response.text

    export_data = export_response.json()

    assert export_data["export_id"] is not None
    assert export_data["project"]["project_id"] == project["project_id"]
    assert export_data["progress"]["total_tasks"] == 1

    history_response = client.get(
        "/reports/exports",
        headers=auth_headers(token),
    )

    assert history_response.status_code == 200, history_response.text

    history_data = history_response.json()

    assert history_data["total"] == 1
    assert history_data["limit"] == 20
    assert history_data["offset"] == 0
    assert len(history_data["items"]) == 1

    item = history_data["items"][0]

    assert item["report_export_id"] == export_data["export_id"]
    assert item["project_id"] == project["project_id"]
    assert item["project_title_snapshot"] == "Report Export History Project"
    assert item["task_count_snapshot"] == 1
    assert item["export_format"] == "json"
    assert item["report_type"] == "project"


def test_admin_can_export_any_personal_project_report(
    client: TestClient,
    db: Session,
) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="report_admin_owner",
        email="report_admin_owner@example.com",
    )
    _admin_id, admin_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="report_admin_user",
        email="report_admin_user@example.com",
    )
    make_admin_directly(db, "report_admin_user@example.com")

    project = create_personal_project(
        client=client,
        token=owner_token,
        title="Admin Export Personal Report Project",
    )

    export_response = client.get(
        f"/reports/projects/{project['project_id']}",
        headers=auth_headers(admin_token),
    )

    assert export_response.status_code == 200, export_response.text

    export_data = export_response.json()

    assert export_data["export_id"] is not None
    assert export_data["project"]["project_id"] == project["project_id"]
    assert export_data["project"]["title"] == "Admin Export Personal Report Project"


def test_project_report_export_history_requires_project_access(
    client: TestClient,
    db: Session,
) -> None:
    _owner_id, owner_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="report_owner",
        email="report_owner@example.com",
    )

    _other_id, other_token = create_verified_user_and_login(
        client=client,
        db=db,
        username="report_other",
        email="report_other@example.com",
    )

    project = create_personal_project(
        client=client,
        token=owner_token,
        title="Private Report History Project",
    )

    export_response = client.get(
        f"/reports/projects/{project['project_id']}",
        headers=auth_headers(owner_token),
    )

    assert export_response.status_code == 200, export_response.text

    blocked_response = client.get(
        f"/reports/projects/{project['project_id']}/exports",
        headers=auth_headers(other_token),
    )

    assert blocked_response.status_code == 404
    assert blocked_response.json()["detail"] == "Project not found"


def test_project_report_export_history_supports_limit_and_offset(
    client: TestClient,
    db: Session,
) -> None:
    _user_id, token = create_verified_user_and_login(
        client=client,
        db=db,
        username="report_pagination_user",
        email="report_pagination_user@example.com",
    )

    project = create_personal_project(
        client=client,
        token=token,
        title="Report Pagination Project",
    )

    first_export_response = client.get(
        f"/reports/projects/{project['project_id']}",
        headers=auth_headers(token),
    )
    second_export_response = client.get(
        f"/reports/projects/{project['project_id']}",
        headers=auth_headers(token),
    )

    assert first_export_response.status_code == 200, first_export_response.text
    assert second_export_response.status_code == 200, second_export_response.text

    history_response = client.get(
        f"/reports/projects/{project['project_id']}/exports?limit=1&offset=1",
        headers=auth_headers(token),
    )

    assert history_response.status_code == 200, history_response.text

    data = history_response.json()

    assert data["total"] == 2
    assert data["limit"] == 1
    assert data["offset"] == 1
    assert len(data["items"]) == 1
