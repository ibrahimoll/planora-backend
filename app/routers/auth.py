import logging
from time import perf_counter
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.core.rate_limit import check_rate_limit
from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    MessageResponse,
    RegisterRequest,
    ResendVerificationCodeRequest,
    ResetPasswordRequest,
    SocialLoginRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
    VerifyPasswordResetCodeRequest,
)
from app.services.auth_service import (
    login_user,
    register_user,
    request_password_reset,
    resend_verification_code,
    reset_password,
    verify_email,
    verify_password_reset_code,
)
from app.services.email_service import EmailDeliveryError
from app.services.profile_service import (
    PROFILE_PICTURE_URL_PREFIX,
    is_profile_picture_data_url,
)
from app.services.social_auth_service import login_with_google

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

logger = logging.getLogger(__name__)

DBSession = Annotated[Session, Depends(get_db)]
LoginForm = Annotated[OAuth2PasswordRequestForm, Depends()]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

EMAIL_DELIVERY_FAILED_MESSAGE = (
    "Email delivery failed. Please try again later or contact support."
)


def serialize_user_response(user: User) -> UserResponse:
    response = UserResponse.model_validate(user)

    if is_profile_picture_data_url(response.profile_pic):
        response.profile_pic = f"{PROFILE_PICTURE_URL_PREFIX}{user.user_id}"

    return response


def _raise_email_delivery_error(exc: EmailDeliveryError) -> None:
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=EMAIL_DELIVERY_FAILED_MESSAGE,
    ) from exc


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: Request,
    data: RegisterRequest,
    db: DBSession,
) -> MessageResponse:
    check_rate_limit(
        request,
        "auth:register",
        limit=3,
        window_seconds=300,
        identifier=data.email,
    )

    try:
        register_user(db, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except EmailDeliveryError as e:
        _raise_email_delivery_error(e)

    return MessageResponse(
        message="Registration successful. Please verify your email."
    )


@router.post("/verify-email")
def verify_user_email(
    request: Request,
    data: VerifyEmailRequest,
    db: DBSession,
) -> TokenResponse:
    check_rate_limit(
        request,
        "auth:verify-email",
        limit=5,
        window_seconds=300,
        identifier=data.email,
    )

    try:
        user = verify_email(db, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return TokenResponse(
        access_token=create_access_token(user.user_id),
    )


@router.post("/resend-verification-code")
def resend_code(
    request: Request,
    data: ResendVerificationCodeRequest,
    db: DBSession,
) -> MessageResponse:
    check_rate_limit(
        request,
        "auth:resend-verification-code",
        limit=3,
        window_seconds=300,
        identifier=data.email,
    )

    try:
        resend_verification_code(db, data)
    except EmailDeliveryError as e:
        _raise_email_delivery_error(e)

    return MessageResponse(
        message="If your account needs verification, a verification code has been sent."
    )


@router.post("/forgot-password")
def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: DBSession,
) -> MessageResponse:
    check_rate_limit(
        request,
        "auth:forgot-password",
        limit=3,
        window_seconds=300,
        identifier=data.email,
    )

    try:
        request_password_reset(db, data)
    except EmailDeliveryError as e:
        _raise_email_delivery_error(e)

    return MessageResponse(
        message="If an account with that email exists, a password reset code has been sent."
    )


@router.post("/verify-reset-code")
def verify_user_password_reset_code(
    request: Request,
    data: VerifyPasswordResetCodeRequest,
    db: DBSession,
) -> MessageResponse:
    check_rate_limit(
        request,
        "auth:verify-reset-code",
        limit=5,
        window_seconds=300,
        identifier=data.email,
    )

    try:
        verify_password_reset_code(db, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return MessageResponse(
        message="Reset code verified successfully."
    )


@router.post("/reset-password")
def reset_user_password(
    request: Request,
    data: ResetPasswordRequest,
    db: DBSession,
) -> MessageResponse:
    check_rate_limit(
        request,
        "auth:reset-password",
        limit=5,
        window_seconds=300,
        identifier=data.email,
    )

    try:
        reset_password(db, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return MessageResponse(
        message="Password reset successfully."
    )


@router.post("/login")
def login(
    request: Request,
    form_data: LoginForm,
    db: DBSession,
) -> TokenResponse:
    started_at = perf_counter()
    identifier_type = "email" if "@" in form_data.username else "username"
    client_host = request.client.host if request.client else "unknown"

    logger.info(
        "auth.login.start identifier_type=%s client_host=%s",
        identifier_type,
        client_host,
    )

    check_rate_limit(
        request,
        "auth:login",
        limit=10,
        window_seconds=60,
        identifier=form_data.username,
    )

    try:
        access_token = login_user(
            db,
            identifier=form_data.username,
            password=form_data.password,
        )
    except ValueError as e:
        error_message = str(e)
        status_label = "unauthorized"

        if error_message == "Invalid username/email or password.":
            total_ms = (perf_counter() - started_at) * 1000
            logger.info(
                "auth.login.finish result=%s identifier_type=%s total_ms=%.2f",
                status_label,
                identifier_type,
                total_ms,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_message,
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

        total_ms = (perf_counter() - started_at) * 1000
        logger.info(
            "auth.login.finish result=forbidden identifier_type=%s total_ms=%.2f",
            identifier_type,
            total_ms,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_message,
        ) from e

    total_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "auth.login.finish result=success identifier_type=%s total_ms=%.2f",
        identifier_type,
        total_ms,
    )

    return TokenResponse(
        access_token=access_token,
    )


@router.post("/google")
def google_login(
    request: Request,
    data: SocialLoginRequest,
    db: DBSession,
) -> TokenResponse:
    started_at = perf_counter()
    client_host = request.client.host if request.client else "unknown"

    logger.info("auth.google.start client_host=%s", client_host)

    check_rate_limit(
        request,
        "auth:google",
        limit=10,
        window_seconds=60,
    )

    try:
        access_token = login_with_google(db, data)
    except ValueError as e:
        error_message = str(e)
        total_ms = (perf_counter() - started_at) * 1000

        logger.info(
            "auth.google.finish result=failure reason=%s total_ms=%.2f",
            error_message,
            total_ms,
        )

        if error_message == "Invalid Google token.":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_message,
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

        if error_message == "Username is required for new Google accounts.":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message,
            ) from e

        if error_message == "Username is already taken.":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_message,
            ) from e

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_message,
        ) from e

    total_ms = (perf_counter() - started_at) * 1000
    logger.info("auth.google.finish result=success total_ms=%.2f", total_ms)

    return TokenResponse(
        access_token=access_token,
    )


@router.get("/me")
def read_current_user(
    current_user: CurrentUser,
) -> UserResponse:
    return serialize_user_response(current_user)
