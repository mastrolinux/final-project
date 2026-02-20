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
    """
    Authentication users table.
    
    Stores authentication credentials with 1:1 relationship to base_profiles.
    Separates authentication concerns from profile data following separation
    of concerns principle.
    
    Fields:
        id: Primary key - authentication user identifier
        user_id: Foreign key to base_profiles.user_id (UNIQUE for 1:1 relationship)
        email: Login email (should match base_profiles.primary_email)
        password_hash: Argon2id hashed password
        provider: OAuth provider name (NULL for email/password users)
        provider_id: Provider-specific user identifier (NULL for email/password users)
        is_email_verified: Email verification status
        email_verified_at: Timestamp when email was verified
        verification_token: Token sent via email for verification
        verification_token_expires_at: Expiration timestamp for verification token
        last_login_at: Timestamp of last successful login
        failed_login_attempts: Counter for failed login attempts
        locked_until: Account locked until this timestamp
        password_changed_at: Timestamp of last password change
        reset_token: Password reset token sent via email
        reset_token_expires_at: Expiration timestamp for reset token
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        deleted_at: Soft delete timestamp
    """
    __tablename__ = "auth_users"
    
    # Primary identification
    id = Column(UUID, primary_key=True, default=lambda: str(uuid_pkg.uuid4()))
    
    # Foreign key to base_profiles (1:1 relationship)
    user_id = Column(
        UUID, 
        ForeignKey("base_profiles.user_id", ondelete="CASCADE"), 
        unique=True, 
        nullable=False,
        index=True
    )
    
    # Login credentials
    email = Column(String, nullable=False, index=True)
    password_hash = Column(String, nullable=False)

    # OAuth provider fields (NULL for email/password users)
    provider = Column(String(50), nullable=True, index=True)  # 'google', 'github', etc.
    provider_id = Column(String(255), nullable=True)  # Provider-specific user ID
    
    # Email verification
    is_email_verified = Column(Boolean, nullable=False, default=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_token = Column(String, nullable=True, index=True)
    verification_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Login tracking and protection
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True, index=True)
    password_changed_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Password reset
    reset_token = Column(String, nullable=True, index=True)
    reset_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Account restoration (after soft deletion)
    restoration_token = Column(String, nullable=True, index=True)
    restoration_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Admin flag - grants access to admin endpoints
    is_admin = Column(Boolean, nullable=False, default=False)

    # Password explicitly set by user (vs. random hash for OAuth users)
    has_custom_password = Column(Boolean, nullable=False, default=False)
    
    # Relationship to base profile
    # base_profile = relationship("BaseProfile", back_populates="auth_user")
    
    def __repr__(self):
        return f"<AuthUser(id={self.id}, email={self.email}, verified={self.is_email_verified})>"
    
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if not self.locked_until:
            return False
        # Ensure both datetimes are timezone-aware for comparison
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
        # Ensure both datetimes are timezone-aware for comparison
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
        # Ensure both datetimes are timezone-aware for comparison
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


# Import uuid for default value
import uuid as uuid_pkg

