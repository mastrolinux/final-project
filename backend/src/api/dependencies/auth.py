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
    """
    Dependency to get the current authenticated user.
    
    Validates JWT access token from Authorization header and returns the AuthUser.
    Raises 401 if token is missing, invalid, or expired.
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        AuthUser model instance
        
    Raises:
        HTTPException 401: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verify the JWT token
    token_data = verify_token(credentials.credentials, token_type="access")
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Get user from database
    auth_repo = AuthRepository(db)
    user = auth_repo.get_by_user_id(token_data.user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if user is soft-deleted
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
    """
    Dependency to optionally get the current authenticated user.
    
    Returns None if no token provided (instead of raising 401).
    Useful for endpoints that work with or without authentication.
    
    Args:
        credentials: Optional Bearer token from Authorization header
        db: Database session
        
    Returns:
        AuthUser model instance or None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def require_admin(
    current_user: AuthUser = Depends(get_current_user)
) -> AuthUser:
    """
    Dependency that requires admin privileges.
    
    Checks for admin status in two ways:
    1. Database flag: auth_users.is_admin = true (source of truth)
    2. Environment: Email in ADMIN_USER_EMAILS (bootstrap/fallback)
    
    Args:
        current_user: Authenticated user from get_current_user
        
    Returns:
        AuthUser if admin, raises 403 otherwise
        
    Raises:
        HTTPException 403: If user is not an admin
    """
    # Check database flag first (source of truth)
    if current_user.is_admin:
        return current_user
    
    # Fallback to environment variable bootstrap list
    if current_user.email.lower() in settings.admin_emails:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )


async def require_verified_user(
    current_user: AuthUser = Depends(get_current_user)
) -> AuthUser:
    """
    Dependency that requires a verified email address.
    
    Args:
        current_user: Authenticated user from get_current_user
        
    Returns:
        AuthUser if email verified, raises 403 otherwise
        
    Raises:
        HTTPException 403: If email not verified
    """
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    
    return current_user
