from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import jwt
from pwdlib import PasswordHash
from app.core.config import settings

password_hasher = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return password_hasher.hash(password)

def verify_password(password: str, stored_password_hash: str) -> bool:
    return password_hasher.verify(password, stored_password_hash)

def hash_verification_code(code: str) -> str:
    return hmac.new(
        settings.verification_code_secret.encode(),
        code.encode(),
        hashlib.sha256,
    ).hexdigest()

def verify_verification_code(code: str, stored_code_hash: str) -> bool:
    submitted_code_hash = hash_verification_code(code)
    return hmac.compare_digest(submitted_code_hash, stored_code_hash)

def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes= settings.access_token_expire_minutes
        )
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_code,
        algorithm= JWT_ALGORITHM
    )
    
def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret_code,
        algorithms= [JWT_ALGORITHM],
    )