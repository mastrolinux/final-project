"""
Authentication Dependencies

FastAPI dependencies for JWT authentication and authorization.
Provides reusable dependencies for protecting endpoints.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import verify_token, TokenData
from src.core.config import settings
from src.models.auth import AuthUser
from src.repositories.auth_repository import AuthRepository


# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> AuthUser:
    """Validate JWT access token and return the authenticated AuthUser."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token_data = verify_token(credentials.credentials, token_type="access")
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    auth_repo = AuthRepository(db)
    user = auth_repo.get_by_user_id(token_data.user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account has been deactivated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Optional[AuthUser]:
    """Like get_current_user but returns None instead of 401 when unauthenticated."""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def require_admin(
    current_user: AuthUser = Depends(get_current_user)
) -> AuthUser:
    """Require admin privileges via database flag or environment bootstrap list."""
    if current_user.is_admin:
        return current_user

    if current_user.email.lower() in settings.admin_emails:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )


async def require_verified_user(
    current_user: AuthUser = Depends(get_current_user)
) -> AuthUser:
    """Require the authenticated user to have a verified email address."""
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    
    return current_user
