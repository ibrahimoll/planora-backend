from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.db.session import get_db
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
)
from app.services.auth_service import (
    login_user,
    register_user,
    request_password_reset,
    resend_verification_code,
    reset_password,
    verify_email,
)
from app.services.social_auth_service import login_with_google

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

DBSession = Annotated[Session, Depends(get_db)]
LoginForm = Annotated[OAuth2PasswordRequestForm, Depends()]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: DBSession,
) -> MessageResponse:
    try:
        register_user(db, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return MessageResponse(
        message="Registration successful. Please verify your email."
    )


@router.post("/verify-email")
def verify_user_email(
    data: VerifyEmailRequest,
    db: DBSession,
) -> MessageResponse:
    try:
        verify_email(db, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return MessageResponse(
        message="Email verified successfully."
    )


@router.post("/resend-verification-code")
def resend_code(
    data: ResendVerificationCodeRequest,
    db: DBSession,
) -> MessageResponse:
    try:
        resend_verification_code(db, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return MessageResponse(
        message="Verification code sent successfully."
    )

@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    db: DBSession,
) ->MessageResponse:
    request_password_reset(db, data)

    return MessageResponse(
        message= "If an account with that email exists, a password reset code has been sent."
    )

@router.post("/reset-password")
def reset_user_password(
    data: ResetPasswordRequest,
    db: DBSession,
) -> MessageResponse:
    try:
        reset_password(db, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return MessageResponse(
        message="Password reset successfully."
    )

@router.post("/login")
def login(
    form_data: LoginForm,
    db: DBSession,
) -> TokenResponse:
    try:
        access_token = login_user(
            db,
            identifier=form_data.username,
            password=form_data.password,
        )
    except ValueError as e:
        error_message = str(e)

        if error_message == "Invalid username/email or password.":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_message,
                headers={"WWW-Authenticate": "Bearer"},
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_message,
        )

    return TokenResponse(
        access_token=access_token,
    )

@router.post("/google")
def google_login(
    data: SocialLoginRequest,
    db: DBSession,
) ->TokenResponse:
    try:
        access_token = login_with_google(db, data)
    except ValueError as e:
        error_message = str(e)

        if error_message =="Invalid Google token.":
            raise HTTPException(
                status_code= status.HTTP_401_UNAUTHORIZED,
                detail= error_message,
                headers= {"WWW-Authenticate" : "Bearer"},
            )
        raise HTTPException(
            status_code= status.HTTP_403_FORBIDDEN,
            detail= error_message
        )
    return TokenResponse(
        access_token= access_token,
    )

@router.get("/me")
def read_current_user(
    current_user: CurrentUser
) -> UserResponse:
    return UserResponse.model_validate(current_user)

