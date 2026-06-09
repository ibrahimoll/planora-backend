from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.project_schema import (
    ProjectCreate,
    ProjectDeleteResponse,
    ProjectMemberInvite,
    ProjectMemberResponse,
    ProjectMemberUpdate,
    ProjectResponse,
    ProjectStatus,
    ProjectUpdate,
)
from app.services.project_service import (
    add_project_member,
    can_manage_project,
    create_personal_project,
    delete_my_personal_project,
    get_manageable_personal_project_by_id,
    get_my_personal_project_by_id,
    get_my_personal_projects,
    get_owned_personal_project_by_id,
    get_project_members,
    get_project_membership,
    get_user_by_email_or_username,
    is_project_owner,
    remove_project_member,
    update_project_member_role,
    update_my_personal_project,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"
PROJECT_MEMBER_NOT_FOUND = "Project member not found"
NOT_ALLOWED = "You are not allowed to perform this action"
USER_NOT_FOUND = "User not found"
ALREADY_PROJECT_MEMBER = "User is already a project member"

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_project(
    project_data: ProjectCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    return create_personal_project(
        db=db,
        project_data=project_data,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=list[ProjectResponse],
)
def get_projects(
    db: DBSession,
    current_user: CurrentUser,
    status: ProjectStatus | None = None,
):
    return get_my_personal_projects(
        db=db,
        current_user=current_user,
        status=status,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
)
def get_project(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_my_personal_project_by_id(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_manageable_personal_project_by_id(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return update_my_personal_project(
        db=db,
        project=project,
        project_data=project_data,
        current_user=current_user,
    )


@router.delete(
    "/{project_id}",
    response_model=ProjectDeleteResponse,
)
def delete_project(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_owned_personal_project_by_id(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    delete_my_personal_project(
        db=db,
        project=project,
    )

    return ProjectDeleteResponse(
        message="Project deleted successfully.",
    )


@router.get(
    "/{project_id}/members",
    response_model=list[ProjectMemberResponse],
)
def list_personal_project_members(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_my_personal_project_by_id(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return get_project_members(
        db=db,
        project_id=project_id,
    )


@router.post(
    "/{project_id}/members/invite",
    response_model=ProjectMemberResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def invite_personal_project_member(
    project_id: int,
    member_data: ProjectMemberInvite,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_manageable_personal_project_by_id(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    user_to_add = get_user_by_email_or_username(
        db=db,
        email_or_username=member_data.email_or_username,
    )

    if (
        user_to_add is None
        or not user_to_add.is_active
        or not user_to_add.is_email_verified
    ):
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=USER_NOT_FOUND,
        )

    existing_project_membership = get_project_membership(
        db=db,
        project_id=project_id,
        user_id=user_to_add.user_id,
    )

    if (
        existing_project_membership is not None
        or user_to_add.user_id == project.created_by
    ):
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=ALREADY_PROJECT_MEMBER,
        )

    return add_project_member(
        db=db,
        project=project,
        user=user_to_add,
        role=member_data.role,
    )


@router.patch(
    "/{project_id}/members/{user_id}",
    response_model=ProjectMemberResponse,
)
def update_personal_project_member_role(
    project_id: int,
    user_id: int,
    member_data: ProjectMemberUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_my_personal_project_by_id(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    current_membership = get_project_membership(
        db=db,
        project_id=project_id,
        user_id=current_user.user_id,
    )

    if (
        current_user.user_id != project.created_by
        and (current_membership is None or not is_project_owner(current_membership))
    ):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    member = get_project_membership(
        db=db,
        project_id=project_id,
        user_id=user_id,
    )

    if member is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_MEMBER_NOT_FOUND,
        )

    if member.role == "owner" or user_id == project.created_by:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Project owner role cannot be changed through this endpoint.",
        )

    return update_project_member_role(
        db=db,
        member=member,
        role=member_data.role,
    )


@router.delete(
    "/{project_id}/members/{user_id}",
    response_model=ProjectDeleteResponse,
)
def remove_personal_project_member(
    project_id: int,
    user_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_manageable_personal_project_by_id(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    if user_id == project.created_by:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Project owner cannot be removed through this endpoint.",
        )

    current_membership = get_project_membership(
        db=db,
        project_id=project_id,
        user_id=current_user.user_id,
    )

    if (
        current_user.user_id != project.created_by
        and (current_membership is None or not can_manage_project(current_membership))
    ):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    member = get_project_membership(
        db=db,
        project_id=project_id,
        user_id=user_id,
    )

    if member is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_MEMBER_NOT_FOUND,
        )

    remove_project_member(
        db=db,
        member=member,
    )

    return ProjectDeleteResponse(
        message="Project member removed successfully.",
    )
