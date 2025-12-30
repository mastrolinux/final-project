"""
Authentication Repository

Data access layer for auth_users table operations.
Handles CRUD operations and authentication-specific queries.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.models.auth import AuthUser


class AuthRepository:
    """Repository for auth_users table operations."""
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get_by_email(self, email: str) -> Optional[AuthUser]:
        """
        Get auth user by email address.
        
        Args:
            email: User email address
            
        Returns:
            AuthUser if found and not deleted, None otherwise
        """
        stmt = select(AuthUser).where(
            AuthUser.email == email,
            AuthUser.deleted_at.is_(None)
        )
        result = self.db.execute(stmt)
        return result.scalars().first()
    
    def get_by_id(self, auth_id: str) -> Optional[AuthUser]:
        """
        Get auth user by auth ID.
        
        Args:
            auth_id: Auth user ID (primary key)
            
        Returns:
            AuthUser if found and not deleted, None otherwise
        """
        stmt = select(AuthUser).where(
            AuthUser.id == auth_id,
            AuthUser.deleted_at.is_(None)
        )
        result = self.db.execute(stmt)
        return result.scalars().first()
    
    def get_by_user_id(self, user_id: str) -> Optional[AuthUser]:
        """
        Get auth user by user_id (foreign key to base_profiles).
        
        Args:
            user_id: User ID from base_profiles table
            
        Returns:
            AuthUser if found and not deleted, None otherwise
        """
        stmt = select(AuthUser).where(
            AuthUser.user_id == user_id,
            AuthUser.deleted_at.is_(None)
        )
        result = self.db.execute(stmt)
        return result.scalars().first()
    
    def get_by_verification_token(self, token: str) -> Optional[AuthUser]:
        """
        Get auth user by verification token.
        
        Args:
            token: Email verification token
            
        Returns:
            AuthUser if found and not deleted, None otherwise
        """
        stmt = select(AuthUser).where(
            AuthUser.verification_token == token,
            AuthUser.deleted_at.is_(None)
        )
        result = self.db.execute(stmt)
        return result.scalars().first()
    
    def get_by_reset_token(self, token: str) -> Optional[AuthUser]:
        """
        Get auth user by password reset token.
        
        Args:
            token: Password reset token
            
        Returns:
            AuthUser if found and not deleted, None otherwise
        """
        stmt = select(AuthUser).where(
            AuthUser.reset_token == token,
            AuthUser.deleted_at.is_(None)
        )
        result = self.db.execute(stmt)
        return result.scalars().first()
    
    def create(self, email: str, password_hash: str, user_id: str) -> AuthUser:
        """
        Create new auth user.
        
        Args:
            email: User email address
            password_hash: Argon2id hashed password
            user_id: Foreign key to base_profiles.user_id
            
        Returns:
            Created AuthUser instance
        """
        auth_user = AuthUser(
            email=email,
            password_hash=password_hash,
            user_id=user_id,
            is_email_verified=False
        )
        self.db.add(auth_user)
        self.db.commit()
        self.db.refresh(auth_user)
        return auth_user
    
    def update_verification_status(self, user_id: str, verified: bool) -> None:
        """
        Update email verification status.
        
        Args:
            user_id: User ID from base_profiles
            verified: New verification status
        """
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.is_email_verified = verified
            auth_user.email_verified_at = datetime.now(timezone.utc) if verified else None
            auth_user.verification_token = None
            auth_user.verification_token_expires_at = None
            self.db.commit()
    
    def set_verification_token(self, user_id: str, token: str, expires_hours: int = 24) -> None:
        """
        Set email verification token.
        
        Args:
            user_id: User ID from base_profiles
            token: Verification token
            expires_hours: Token expiration in hours (default 24)
        """
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.verification_token = token
            auth_user.verification_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
            self.db.commit()
    
    def set_reset_token(self, user_id: str, token: str, expires_hours: int = 1) -> None:
        """
        Set password reset token.
        
        Args:
            user_id: User ID from base_profiles
            token: Reset token
            expires_hours: Token expiration in hours (default 1)
        """
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.reset_token = token
            auth_user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
            self.db.commit()
    
    def clear_reset_token(self, user_id: str) -> None:
        """
        Clear password reset token after use.
        
        Args:
            user_id: User ID from base_profiles
        """
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.reset_token = None
            auth_user.reset_token_expires_at = None
            self.db.commit()
    
    def update_password(self, user_id: str, password_hash: str) -> None:
        """
        Update user password hash.
        
        Args:
            user_id: User ID from base_profiles
            password_hash: New Argon2id hashed password
        """
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.password_hash = password_hash
            auth_user.password_changed_at = datetime.now(timezone.utc)
            self.db.commit()
    
    def increment_failed_login(self, user_id: str) -> int:
        """
        Increment failed login attempts counter.
        
        Locks account after 5 failed attempts for 15 minutes.
        
        Args:
            user_id: User ID from base_profiles
            
        Returns:
            New failed login attempts count
        """
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.failed_login_attempts += 1
            
            # Lock account after 5 failed attempts
            if auth_user.failed_login_attempts >= 5:
                auth_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            
            self.db.commit()
            return auth_user.failed_login_attempts
        return 0
    
    def reset_failed_login(self, user_id: str) -> None:
        """
        Reset failed login attempts after successful login.
        
        Args:
            user_id: User ID from base_profiles
        """
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.failed_login_attempts = 0
            auth_user.locked_until = None
            auth_user.last_login_at = datetime.now(timezone.utc)
            self.db.commit()
    
    def soft_delete(self, user_id: str) -> None:
        """
        Soft delete auth user (30-day grace period).
        
        Args:
            user_id: User ID from base_profiles
        """
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.deleted_at = datetime.now(timezone.utc)
            self.db.commit()

