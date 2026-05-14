import string
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def validate_password_strength(password: str) -> str:
    if not any(char.isupper() for char in password):
        raise ValueError("Password must contain at least one uppercase letter.")

    if not any(char in string.punctuation for char in password):
        raise ValueError("Password must contain at least one symbol.")

    return password


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=150)

    @field_validator("password")
    @classmethod
    def validate_register_password_strength(cls, password: str) -> str:
        return validate_password_strength(password)


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendVerificationCodeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr

class SocialLoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace= True)

    id_token: str = Field(min_length= 10)
    username: str | None = Field(default=None, min_length=3, max_length=50)
    full_name: str | None = Field(default = None, max_length= 150)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    is_email_verified: bool
    profile_pic: str | None
    created_at: datetime


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, password: str) -> str:
        return validate_password_strength(password)
    