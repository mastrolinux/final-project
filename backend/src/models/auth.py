"""
Authentication Models

SQLAlchemy models for authentication users table.
Implements authentication aggregate with 1:1 relationship to base_profiles.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from src.core.database import Base
from src.models.profile import UUID


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SoftDeleteMixin:
    """Mixin for soft delete support."""
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class AuthUser(Base, TimestampMixin, SoftDeleteMixin):
    """Authentication credentials with 1:1 relationship to base_profiles."""
    __tablename__ = "auth_users"
    
    id = Column(UUID, primary_key=True, default=lambda: str(uuid_pkg.uuid4()))

    user_id = Column(
        UUID, 
        ForeignKey("base_profiles.user_id", ondelete="CASCADE"), 
        unique=True, 
        nullable=False,
        index=True
    )
    
    email = Column(String, nullable=False, index=True)
    password_hash = Column(String, nullable=False)

    provider = Column(String(50), nullable=True, index=True)
    provider_id = Column(String(255), nullable=True)

    is_email_verified = Column(Boolean, nullable=False, default=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_token = Column(String, nullable=True, index=True)
    verification_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True, index=True)
    password_changed_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )
    
    reset_token = Column(String, nullable=True, index=True)
    reset_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    restoration_token = Column(String, nullable=True, index=True)
    restoration_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    is_admin = Column(Boolean, nullable=False, default=False)
    has_custom_password = Column(Boolean, nullable=False, default=False)
    
    def __repr__(self):
        return f"<AuthUser(id={self.id}, email={self.email}, verified={self.is_email_verified})>"
    
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if not self.locked_until:
            return False
        locked_until = self.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return locked_until > datetime.now(timezone.utc)
    
    def is_verification_token_valid(self, token: str) -> bool:
        """Check if verification token is valid and not expired."""
        if not self.verification_token or self.verification_token != token:
            return False
        if not self.verification_token_expires_at:
            return False
        expires_at = self.verification_token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at > datetime.now(timezone.utc)
    
    def is_reset_token_valid(self, token: str) -> bool:
        """Check if reset token is valid and not expired."""
        if not self.reset_token or self.reset_token != token:
            return False
        if not self.reset_token_expires_at:
            return False
        expires_at = self.reset_token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at > datetime.now(timezone.utc)

    def is_restoration_token_valid(self, token: str) -> bool:
        """Check if restoration token is valid and not expired."""
        if not self.restoration_token or self.restoration_token != token:
            return False
        if not self.restoration_token_expires_at:
            return False
        expires_at = self.restoration_token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at > datetime.now(timezone.utc)

    @property
    def is_deleted(self) -> bool:
        """Check if account is soft-deleted."""
        return self.deleted_at is not None


import uuid as uuid_pkg

