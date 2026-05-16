from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "/auth/login")

DBsession = Annotated[Session, Depends(get_db)]
Token = Annotated[str, Depends(oauth2_scheme)]

def get_current_user(
        token: Token,
        db: DBsession,
) -> User:
    credentials_exception = HTTPException(
        status_code= status.HTTP_401_UNAUTHORIZED,
        detail= "Could not validate credentials.",
        headers = {"WWW-Authenticate" : "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception
        
        user_id = int(user_id)
    except(jwt.InvalidTokenError, ValueError, TypeError):
        raise credentials_exception
    
    user = db.scalar(
        select(User).where(User.user_id == user_id)
    )

    if user is None:
        raise credentials_exception
    
    return user

def get_current_active_verified_user(
current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code= status.HTTP_403_FORBIDDEN,
            detail= "Account is deactivated.",
        )
    
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code= status.HTTP_403_FORBIDDEN,
            detail= "Email is not verified.",
        )
    
    return current_user


def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_active_verified_user)],
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    return current_user