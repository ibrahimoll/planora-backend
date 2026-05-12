from dataclasses import dataclass

from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings

@dataclass(frozen=True)
class GoogleUserInfo:
    provider_user_id: str
    email: str
    email_verified: bool
    full_name: str | None
    profile_pic : str | None

def verify_google_id_token(token: str) -> GoogleUserInfo:
    try:
        id_info = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.google_client_id,
        )
    except (ValueError, GoogleAuthError):
        raise ValueError("Invalid Google token.")

    provider_user_id= id_info.get("sub")
    email = id_info.get("email")
    email_verified = id_info.get("email_verified", False)
    full_name = id_info.get("name")
    profile_pic = id_info.get("picure")

    if not provider_user_id:
        raise ValueError("Google token is missing user ID.")
    
    if not email:
        raise ValueError("Google token is missing email.")
    
    if not email_verified:
        raise ValueError("Google email is not verified.")
    
    return GoogleUserInfo(
        provider_user_id= provider_user_id,
        email =email.lower(),
        email_verified= bool(email_verified),
        full_name= full_name,
        profile_pic=profile_pic,
    )