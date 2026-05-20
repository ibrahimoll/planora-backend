from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db.session import SessionLocal
from app.models.activity_log import ActivityLog
from app.models.admin_log import AdminLog
from app.models.notification import Notification
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.report_export import ReportExport
from app.models.risk_analysis import RiskAnalysis
from app.models.task import Task
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.user import User

NOW = datetime.now(timezone.utc)


def env_int(name: str) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return int(raw_value)


def optional_env_int(name: str) -> int | None:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return None
    return int(raw_value)


def load_user(db: Session, user_id: int, label: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise RuntimeError(f"{label} user does not exist: {user_id}")
    return user


def load_optional_user(db: Session, user_id: int | None, label: str) -> User | None:
    if user_id is None:
        return None
    return load_user(db, user_id, label)


def ensure_team(db: Session, name: str, creator: User) -> Team:
    team = db.scalar(select(Team).where(Team.name == name))
    if team is not None:
        return team
    team = Team(name=name, created_by=creator.user_id)
    db.add(team)
    db.flush()
    return team


def ensure_team_member(db: Session, team: Team, user: User, role: str) -> None:
    row = db.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team.team_id,
            TeamMember.user_id == user.user_id,
        )
    )
    if row is None:
        db.add(TeamMember(team_id=team.team_id, user_id=user.user_id, role=role))
    else:
        row.role = role
    db.flush()


def ensure_project(
    db: Session,
    title: str,
    creator: User,
    project_type: str,
    status: str,
    deadline_days: int,
    description: str,
    team: Team | None = None,
) -> Project:
    project = db.scalar(select(Project).where(Project.title == title))
    if project is not None:
        return project
    project = Project(
        created_by=creator.user_id,
        team_id=None if team is None else team.team_id,
        title=title,
        description=description,
        deadline=NOW + timedelta(days=deadline_days),
        status=status,
        project_type=project_type,
    )
    db.add(project)
    db.flush()
    return project


def ensure_project_member(db: Session, project: Project, user: User, role: str) -> None:
    row = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.project_id,
            ProjectMember.user_id == user.user_id,
        )
    )
    if row is None:
        db.add(ProjectMember(project_id=project.project_id, user_id=user.user_id, role=role))
    else:
        row.role = role
    db.flush()


def ensure_task(
    db: Session,
    project: Project,
    creator: User,
    title: str,
    status: str,
    priority: str,
    due_days: int,
    estimated_hours: str,
    assignee: User | None = None,
    actual_hours: str | None = None,
) -> Task:
    task = db.scalar(
        select(Task).where(Task.project_id == project.project_id, Task.title == title)
    )
    if task is not None:
        return task
    task = Task(
        project_id=project.project_id,
        assigned_to=None if assignee is None else assignee.user_id,
        created_by=creator.user_id,
        title=title,
        description="Seeded for Step 34 browser QA.",
        priority=priority,
        estimated_hours=Decimal(estimated_hours),
        actual_hours=None if actual_hours is None else Decimal(actual_hours),
        status=status,
        due_date=NOW + timedelta(days=due_days),
        completed_at=NOW - timedelta(days=1) if status == "completed" else None,
    )
    db.add(task)
    db.flush()
    return task


def ensure_risk(db: Session, project: Project, level: str, delay_days: int) -> None:
    row = db.scalar(
        select(RiskAnalysis).where(
            RiskAnalysis.project_id == project.project_id,
            RiskAnalysis.risk_level == level,
        )
    )
    if row is None:
        db.add(
            RiskAnalysis(
                project_id=project.project_id,
                risk_level=level,
                predicted_delay_days=delay_days,
                reason="Seeded risk data for browser QA.",
                recommendation="Review blocked or overdue tasks before the demo.",
            )
        )
        db.flush()


def ensure_notification(db: Session, user: User, title: str, kind: str) -> None:
    row = db.scalar(
        select(Notification).where(Notification.user_id == user.user_id, Notification.title == title)
    )
    if row is None:
        db.add(
            Notification(
                user_id=user.user_id,
                title=title,
                message="Seeded notification for Step 34 browser QA.",
                type=kind,
                is_read=False,
            )
        )
        db.flush()


def ensure_activity(db: Session, project: Project, actor: User, task: Task | None, event_type: str) -> None:
    message = f"Seeded {event_type} activity for Step 34 browser QA."
    row = db.scalar(
        select(ActivityLog).where(
            ActivityLog.project_id == project.project_id,
            ActivityLog.event_type == event_type,
            ActivityLog.message == message,
        )
    )
    if row is None:
        db.add(
            ActivityLog(
                project_id=project.project_id,
                task_id=None if task is None else task.task_id,
                actor_id=actor.user_id,
                event_type=event_type,
                actor_username_snapshot=actor.username,
                actor_full_name_snapshot=actor.full_name,
                task_title_snapshot=None if task is None else task.title,
                message=message,
                metadata_json={"seeded_for": "step_34_browser_qa"},
            )
        )
        db.flush()


def ensure_report_export(db: Session, project: Project, exporter: User, task_count: int) -> None:
    row = db.scalar(
        select(ReportExport).where(
            ReportExport.project_id == project.project_id,
            ReportExport.exported_by == exporter.user_id,
        )
    )
    if row is None:
        db.add(
            ReportExport(
                project_id=project.project_id,
                exported_by=exporter.user_id,
                report_type="project",
                export_format="json",
                project_title_snapshot=project.title,
                project_status_snapshot=project.status,
                project_type_snapshot=project.project_type,
                task_count_snapshot=task_count,
                completion_percentage_snapshot=Decimal("33.33"),
                exported_by_username_snapshot=exporter.username,
                exported_by_full_name_snapshot=exporter.full_name,
                metadata_json={"seeded_for": "step_34_browser_qa"},
            )
        )
        db.flush()


def ensure_admin_log(db: Session, admin: User, target: User | None, action: str) -> None:
    row = db.scalar(
        select(AdminLog).where(AdminLog.admin_id == admin.user_id, AdminLog.action == action)
    )
    if row is None:
        db.add(
            AdminLog(
                admin_id=admin.user_id,
                target_user_id=None if target is None else target.user_id,
                action=action,
            )
        )
        db.flush()


def seed_browser_qa_data() -> None:
    db = SessionLocal()
    try:
        admin = load_user(db, env_int("PLANORA_QA_ADMIN_ID"), "admin")
        owner = load_user(db, env_int("PLANORA_QA_OWNER_ID"), "owner")
        manager = load_optional_user(db, optional_env_int("PLANORA_QA_MANAGER_ID"), "manager")
        member = load_optional_user(db, optional_env_int("PLANORA_QA_MEMBER_ID"), "member")

        team = ensure_team(db, "Planora QA Demo Team", owner)
        ensure_team_member(db, team, owner, "owner")
        ensure_team_member(db, team, admin, "admin")

        if manager is not None and manager.user_id not in {owner.user_id, admin.user_id}:
            ensure_team_member(db, team, manager, "admin")

        if member is not None and member.user_id not in {owner.user_id, admin.user_id}:
            ensure_team_member(db, team, member, "member")

        personal_project = ensure_project(
            db,
            "QA Personal Launch Plan",
            owner,
            "personal",
            "in_progress",
            14,
            "Personal project for Step 34 browser QA.",
        )
        team_project = ensure_project(
            db,
            "QA Team Product Release",
            owner,
            "team",
            "in_progress",
            21,
            "Team project for Step 34 browser QA.",
            team,
        )
        ensure_project_member(db, team_project, owner, "owner")
        ensure_project_member(db, team_project, admin, "manager")

        if manager is not None and manager.user_id not in {owner.user_id, admin.user_id}:
            ensure_project_member(db, team_project, manager, "manager")

        if member is not None and member.user_id not in {owner.user_id, admin.user_id}:
            ensure_project_member(db, team_project, member, "member")

        team_second_assignee = manager or admin
        team_third_assignee = member or owner

        personal_done = ensure_task(db, personal_project, owner, "QA personal completed task", "completed", "medium", -2, "2.00", owner, "2.50")
        ensure_task(db, personal_project, owner, "QA personal in-progress task", "in_progress", "high", 3, "3.00", owner)
        ensure_task(db, personal_project, owner, "QA personal blocked task", "blocked", "high", -1, "4.00", owner)

        team_done = ensure_task(db, team_project, owner, "QA team completed task", "completed", "medium", -3, "3.00", team_second_assignee, "3.50")
        ensure_task(db, team_project, owner, "QA team mobile overview task", "in_progress", "high", 5, "6.00", team_third_assignee)
        ensure_task(db, team_project, owner, "QA team blocked integration task", "blocked", "high", -2, "5.00", team_second_assignee)

        ensure_risk(db, personal_project, "medium", 2)
        ensure_risk(db, team_project, "high", 5)

        ensure_notification(db, owner, "QA deadline reminder", "deadline")
        ensure_notification(db, admin, "QA high-risk project", "risk")
        ensure_notification(db, team_third_assignee, "QA task assignment", "task")

        ensure_activity(db, personal_project, owner, None, "project_created")
        ensure_activity(db, personal_project, owner, personal_done, "task_completed")
        ensure_activity(db, team_project, team_second_assignee, team_done, "task_completed")

        ensure_report_export(db, personal_project, owner, 3)
        ensure_report_export(db, team_project, team_second_assignee, 3)

        ensure_admin_log(db, admin, owner, "Seeded Step 34 browser QA data")
        ensure_admin_log(db, admin, team_second_assignee, "Reviewed Step 34 browser QA workload")

        db.commit()
        print("Step 34 browser QA data seeded successfully.")
        print("Required users used:")
        print(f"  Admin ID: {admin.user_id}")
        print(f"  Owner ID: {owner.user_id}")
        print("Optional manager/member IDs were used only if provided.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_browser_qa_data()
