from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user, get_current_admin_user
from app.models.report_request import ReportRequest
from app.models.user import User
from app.schemas.notification_schema import NotificationType
from app.schemas.report_delivery_schema import (
    ReportDeliveryRequest,
    ReportDeliveryResponse,
    ReportRequestTokenResponse,
)
from app.schemas.report_request_schema import (
    ReportRequestActionResponse,
    ReportRequestItem,
    ReportRequestListResponse,
    ReportRequestProjectSummary,
    ReportRequestReadyRequest,
    ReportRequestRejectRequest,
    ReportRequestUserSummary,
)
from app.schemas.report_schema import (
    ProjectReportResponse,
    ReportExportHistoryListResponse,
    ReportRequestResponse,
)
from app.services.email_service import EmailDeliveryError
from app.services.notification_service import create_notification
from app.services.report_delivery_service import send_project_report_delivery
from app.services.report_request_email_service import send_actionable_report_request_email
from app.services.report_request_token_service import resolve_report_request_token
from app.services.report_service import (
    create_report_export_history,
    generate_project_report,
    get_accessible_project_for_report,
    list_my_report_exports,
    list_project_report_exports,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin_user)]

PROJECT_NOT_FOUND = "Project not found"
REPORT_NOT_READY = "No admin-approved report is ready for this project yet"
INVALID_REPORT_TOKEN = "Invalid or expired report request token"
REPORT_REQUEST_NOT_FOUND = "Report request not found"

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


def unique_admin_recipients(admins: list[User]) -> list[User]:
    seen_emails: set[str] = set()
    recipients: list[User] = []

    for admin in admins:
        normalized_email = admin.email.strip().lower()
        if not normalized_email or normalized_email in seen_emails:
            continue
        seen_emails.add(normalized_email)
        recipients.append(admin)

    return recipients


def find_user_by_email(db: Session, address: str) -> User | None:
    normalized_email = address.strip().lower()
    if not normalized_email:
        return None

    return (
        db.query(User)
        .filter(
            User.email.ilike(normalized_email),
            User.is_active.is_(True),
        )
        .first()
    )


def build_report_request_item(request: ReportRequest) -> ReportRequestItem:
    project = request.project
    requester = request.requester

    return ReportRequestItem(
        report_request_id=request.report_request_id,
        project=ReportRequestProjectSummary(
            project_id=project.project_id,
            title=project.title,
            project_type=project.project_type,
            status=project.status,
        ),
        requester=ReportRequestUserSummary(
            user_id=requester.user_id if requester else None,
            full_name=requester.full_name if requester else None,
            email=requester.email if requester else None,
            username=requester.username if requester else None,
        ),
        status=request.status,
        admin_note=request.admin_note,
        rejection_reason=request.rejection_reason,
        report_export_id=request.report_export_id,
        requested_at=request.requested_at,
        resolved_at=request.resolved_at,
    )


def get_report_request_or_404(db: Session, request_id: int) -> ReportRequest:
    request = db.get(ReportRequest, request_id)

    if request is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=REPORT_REQUEST_NOT_FOUND,
        )

    return request


def find_latest_request_for_user_project(
    db: Session,
    *,
    project_id: int,
    user_id: int | None,
) -> ReportRequest | None:
    if user_id is None:
        return None

    stmt = (
        select(ReportRequest)
        .where(
            ReportRequest.project_id == project_id,
            ReportRequest.requested_by_user_id == user_id,
        )
        .order_by(ReportRequest.requested_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def notify_report_ready(
    db: Session,
    *,
    request: ReportRequest,
    admin: User,
) -> None:
    requester = request.requester
    if requester is None:
        return

    create_notification(
        db=db,
        user_id=requester.user_id,
        title="Project report ready",
        message=f'Your report for "{request.project.title}" is ready. Open the project Reports card to view it.',
        notification_type=NotificationType.SYSTEM,
        commit=True,
        send_push=True,
    )

    send_project_report_delivery(
        address=requester.email,
        name=requester.full_name,
        admin_name=admin.full_name,
        note=request.admin_note,
        report=generate_project_report(db=db, project=request.project),
    )


@router.get(
    "/requests/resolve",
    response_model=ReportRequestTokenResponse,
)
def resolve_report_request(
    token: str,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    payload = resolve_report_request_token(token)

    if payload is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=INVALID_REPORT_TOKEN,
        )

    project_id = int(payload["project_id"])
    address = str(payload["requester_email"])
    requester = find_user_by_email(db, address)
    request = find_latest_request_for_user_project(
        db,
        project_id=project_id,
        user_id=requester.user_id if requester else None,
    )

    return ReportRequestTokenResponse(
        project_id=project_id,
        address=address,
        name=str(payload.get("requester_name") or "") or None,
        request_id=request.report_request_id if request else None,
        status=request.status if request else None,
    )


@router.get(
    "/requests/me",
    response_model=ReportRequestListResponse,
)
def list_my_report_requests(
    db: DBSession,
    current_user: CurrentUser,
    project_id: int | None = Query(default=None),
):
    stmt = select(ReportRequest).where(
        ReportRequest.requested_by_user_id == current_user.user_id,
    )

    if project_id is not None:
        project = get_accessible_project_for_report(
            db=db,
            project_id=project_id,
            current_user=current_user,
        )
        if project is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=PROJECT_NOT_FOUND,
            )
        stmt = stmt.where(ReportRequest.project_id == project_id)

    stmt = stmt.order_by(ReportRequest.requested_at.desc())
    items = list(db.execute(stmt).scalars().all())

    return ReportRequestListResponse(
        items=[build_report_request_item(item) for item in items],
        total=len(items),
    )


@router.get(
    "/admin/requests",
    response_model=ReportRequestListResponse,
)
def list_admin_report_requests(
    db: DBSession,
    current_admin: CurrentAdmin,
    status: str | None = Query(default="pending"),
):
    stmt = select(ReportRequest)

    if status and status != "all":
        stmt = stmt.where(ReportRequest.status == status)

    stmt = stmt.order_by(ReportRequest.requested_at.desc())
    items = list(db.execute(stmt).scalars().all())

    return ReportRequestListResponse(
        items=[build_report_request_item(item) for item in items],
        total=len(items),
    )


@router.post(
    "/admin/requests/{request_id}/ready",
    response_model=ReportRequestActionResponse,
)
def mark_report_request_ready(
    request_id: int,
    payload: ReportRequestReadyRequest,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    request = get_report_request_or_404(db, request_id)

    report = generate_project_report(
        db=db,
        project=request.project,
    )
    export = create_report_export_history(
        db=db,
        project=request.project,
        current_user=current_admin,
        report=report,
    )

    request.status = "ready"
    request.admin_note = payload.note
    request.rejection_reason = None
    request.report_export_id = export.report_export_id
    request.resolved_by_admin_id = current_admin.user_id
    request.resolved_at = datetime.now(timezone.utc)
    request.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(request)

    try:
        notify_report_ready(db, request=request, admin=current_admin)
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail="Report was marked ready, but the ready email could not be sent.",
        ) from exc

    return ReportRequestActionResponse(
        message="Report marked ready and user was notified.",
        request=build_report_request_item(request),
    )


@router.post(
    "/admin/requests/{request_id}/reject",
    response_model=ReportRequestActionResponse,
)
def reject_report_request(
    request_id: int,
    payload: ReportRequestRejectRequest,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    request = get_report_request_or_404(db, request_id)

    request.status = "rejected"
    request.rejection_reason = payload.reason
    request.resolved_by_admin_id = current_admin.user_id
    request.resolved_at = datetime.now(timezone.utc)
    request.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(request)

    if request.requester is not None:
        create_notification(
            db=db,
            user_id=request.requester.user_id,
            title="Report request rejected",
            message=f'Your report request for "{request.project.title}" was rejected.',
            notification_type=NotificationType.SYSTEM,
            commit=True,
            send_push=True,
        )

    return ReportRequestActionResponse(
        message="Report request rejected.",
        request=build_report_request_item(request),
    )


@router.get(
    "/projects/{project_id}",
    response_model=ProjectReportResponse,
)
def export_project_report(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_accessible_project_for_report(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    report = generate_project_report(
        db=db,
        project=project,
    )

    export = create_report_export_history(
        db=db,
        project=project,
        current_user=current_user,
        report=report,
    )

    return report.model_copy(
        update={
            "export_id": export.report_export_id,
        }
    )


@router.get(
    "/projects/{project_id}/latest",
    response_model=ProjectReportResponse,
)
def get_latest_ready_project_report(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_accessible_project_for_report(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    exports = list_project_report_exports(
        db=db,
        project=project,
        limit=1,
        offset=0,
    )

    if not exports.items:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=REPORT_NOT_READY,
        )

    report = generate_project_report(
        db=db,
        project=project,
    )

    return report.model_copy(
        update={
            "export_id": exports.items[0].report_export_id,
        }
    )


@router.post(
    "/projects/{project_id}/request",
    response_model=ReportRequestResponse,
    status_code=http_status.HTTP_202_ACCEPTED,
)
def request_project_report(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_accessible_project_for_report(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    # Lock this user's row until the pending request check and insert
    # are complete. This prevents two simultaneous mobile requests
    # from both sending an email to the admins.
    db.execute(
        select(User)
        .where(User.user_id == current_user.user_id)
        .with_for_update()
    ).scalar_one()

    existing_pending = (
        db.execute(
            select(ReportRequest)
            .where(
                ReportRequest.project_id == project.project_id,
                ReportRequest.requested_by_user_id == current_user.user_id,
                ReportRequest.status == "pending",
            )
            .order_by(ReportRequest.requested_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )

    # A request already exists, so do not create another row
    # and do not notify the admins again.
    if existing_pending is not None:
        db.commit()

        return ReportRequestResponse(
            message="A report request is already pending.",
            project_id=project.project_id,
            project_title=project.title,
            requested_at=existing_pending.requested_at,
            notified_admin_count=0,
        )

    report_request = ReportRequest(
        project_id=project.project_id,
        requested_by_user_id=current_user.user_id,
        status="pending",
    )

    db.add(report_request)
    db.commit()
    db.refresh(report_request)

    admins = (
        db.query(User)
        .filter(
            User.role == "admin",
            User.is_active.is_(True),
            User.is_email_verified.is_(True),
        )
        .all()
    )

    # Prevent duplicate emails when multiple admin rows use
    # the same email address.
    recipients = unique_admin_recipients(admins)

    if not recipients:
        db.delete(report_request)
        db.commit()

        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No verified active admin is available "
                "to receive report requests."
            ),
        )

    delivered_count = 0

    for admin in recipients:
        try:
            send_actionable_report_request_email(
                recipient_email=admin.email,
                admin_name=admin.full_name,
                requester_name=current_user.full_name,
                requester_email=current_user.email,
                project_title=project.title,
                project_id=project.project_id,
                project_type=project.project_type,
            )

            delivered_count += 1

        except EmailDeliveryError:
            continue

    if delivered_count == 0:

        db.delete(report_request)
        db.commit()

        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail="Report request could not be emailed to admins.",
        )

    return ReportRequestResponse(
        message="Report request sent to admin.",
        project_id=project.project_id,
        project_title=project.title,
        requested_at=report_request.requested_at,
        notified_admin_count=delivered_count,
    )


@router.post(
    "/projects/{project_id}/deliver",
    response_model=ReportDeliveryResponse,
)
def deliver_project_report(
    project_id: int,
    payload: ReportDeliveryRequest,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    address = payload.address.strip()

    if not address:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Recipient address is required.",
        )

    project = get_accessible_project_for_report(
        db=db,
        project_id=project_id,
        current_user=current_admin,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    report = generate_project_report(
        db=db,
        project=project,
    )

    export = create_report_export_history(
        db=db,
        project=project,
        current_user=current_admin,
        report=report,
    )

    recipient_user = find_user_by_email(db, address)
    related_request = find_latest_request_for_user_project(
        db,
        project_id=project.project_id,
        user_id=recipient_user.user_id if recipient_user else None,
    )

    if related_request is not None:
        related_request.status = "ready"
        related_request.admin_note = payload.note
        related_request.rejection_reason = None
        related_request.report_export_id = export.report_export_id
        related_request.resolved_by_admin_id = current_admin.user_id
        related_request.resolved_at = datetime.now(timezone.utc)
        related_request.updated_at = datetime.now(timezone.utc)
        db.commit()

    if recipient_user is not None:
        create_notification(
            db=db,
            user_id=recipient_user.user_id,
            title="Project report ready",
            message=f'Your report for "{project.title}" is ready. Open the project Reports card to view it.',
            notification_type=NotificationType.SYSTEM,
            commit=True,
            send_push=True,
        )

    try:
        send_project_report_delivery(
            address=address,
            name=payload.name,
            admin_name=current_admin.full_name,
            note=payload.note,
            report=report,
        )
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail="Report ready email could not be sent to the recipient.",
        ) from exc

    return ReportDeliveryResponse(
        message="Project report marked ready and user was notified.",
        project_id=project.project_id,
        project_title=project.title,
        address=address,
        delivered_at=datetime.now(timezone.utc),
        export_id=export.report_export_id,
    )


@router.get(
    "/exports",
    response_model=ReportExportHistoryListResponse,
)
def get_my_report_export_history(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return list_my_report_exports(
        db=db,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/projects/{project_id}/exports",
    response_model=ReportExportHistoryListResponse,
)
def get_project_report_export_history(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    project = get_accessible_project_for_report(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return list_project_report_exports(
        db=db,
        project=project,
        limit=limit,
        offset=offset,
    )
