from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.auth import UserResponse, validate_password_strength

PROFILE_PICTURE_URL_PREFIX = "/profile/picture/"
PROFILE_PICTURE_DATA_URL_PREFIX = "data:image/"


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str | None = Field(default=None, min_length=3, max_length=50)
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    profile_pic: str | None = Field(default=None, max_length=1000)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, password: str) -> str:
        return validate_password_strength(password)
    

class ProfileResponse(UserResponse):
    @field_serializer("profile_pic")
    def serialize_profile_pic(self, profile_pic: str | None) -> str | None:
        if not profile_pic:
            return None

        if profile_pic.startswith(PROFILE_PICTURE_DATA_URL_PREFIX) and ";base64," in profile_pic:
            return f"{PROFILE_PICTURE_URL_PREFIX}{self.user_id}"

        return profile_pic


class ProfileUpdateResponse(BaseModel):
    message: str
    user: ProfileResponse


class ChangePasswordResponse(BaseModel):
    message: str


class DeleteAccountRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    current_password: str = Field(min_length=1, max_length=128)
    confirmation_text: str = Field(min_length=1, max_length=50)


class DeleteAccountResponse(BaseModel):
    message: str
