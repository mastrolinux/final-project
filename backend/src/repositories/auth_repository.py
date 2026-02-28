"""
Authentication Repository

Data access layer for auth_users table operations.
Handles CRUD operations and authentication-specific queries.
"""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.auth import AuthUser


class AuthRepository:
    """Repository for auth_users table operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> AuthUser | None:
        """Get auth user by email address, excluding soft-deleted."""
        stmt = select(AuthUser).where(AuthUser.email == email, AuthUser.deleted_at.is_(None))
        result = self.db.execute(stmt)
        return result.scalars().first()

    def get_by_id(self, auth_id: str) -> AuthUser | None:
        """Get auth user by auth ID, excluding soft-deleted."""
        stmt = select(AuthUser).where(AuthUser.id == auth_id, AuthUser.deleted_at.is_(None))
        result = self.db.execute(stmt)
        return result.scalars().first()

    def get_by_user_id(self, user_id: str) -> AuthUser | None:
        """Get auth user by user_id (FK to base_profiles), excluding soft-deleted."""
        stmt = select(AuthUser).where(AuthUser.user_id == user_id, AuthUser.deleted_at.is_(None))
        result = self.db.execute(stmt)
        return result.scalars().first()

    def get_by_verification_token(self, token: str) -> AuthUser | None:
        """Get auth user by email verification token, excluding soft-deleted."""
        stmt = select(AuthUser).where(
            AuthUser.verification_token == token, AuthUser.deleted_at.is_(None)
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    def get_by_reset_token(self, token: str) -> AuthUser | None:
        """Get auth user by password reset token, excluding soft-deleted."""
        stmt = select(AuthUser).where(AuthUser.reset_token == token, AuthUser.deleted_at.is_(None))
        result = self.db.execute(stmt)
        return result.scalars().first()

    def get_by_provider(self, provider: str, provider_id: str) -> AuthUser | None:
        """Get auth user by OAuth provider and provider ID, excluding soft-deleted."""
        stmt = select(AuthUser).where(
            AuthUser.provider == provider,
            AuthUser.provider_id == provider_id,
            AuthUser.deleted_at.is_(None),
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    def get_by_provider_including_deleted(self, provider: str, provider_id: str) -> AuthUser | None:
        """Get auth user by OAuth provider and provider ID, including soft-deleted.

        Used for restoration detection during OAuth login.
        """
        stmt = select(AuthUser).where(
            AuthUser.provider == provider, AuthUser.provider_id == provider_id
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    def create(self, email: str, password_hash: str, user_id: str) -> AuthUser:
        """Create new auth user for email/password authentication."""
        auth_user = AuthUser(
            email=email,
            password_hash=password_hash,
            user_id=user_id,
            is_email_verified=False,
            has_custom_password=True,
        )
        self.db.add(auth_user)
        self.db.commit()
        self.db.refresh(auth_user)
        return auth_user

    def create_user(
        self,
        email: str,
        password_hash: str,
        user_id: str,
        is_email_verified: bool = False,
        provider: str | None = None,
        provider_id: str | None = None,
    ) -> AuthUser:
        """Create new auth user (email/password or OAuth)."""
        auth_user = AuthUser(
            email=email,
            password_hash=password_hash,
            user_id=user_id,
            is_email_verified=is_email_verified,
            provider=provider,
            provider_id=provider_id,
        )
        self.db.add(auth_user)
        self.db.commit()
        self.db.refresh(auth_user)
        return auth_user

    def update_verification_status(self, user_id: str, verified: bool) -> None:
        """Update email verification status and clear the verification token."""
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.is_email_verified = verified
            auth_user.email_verified_at = datetime.now(UTC) if verified else None
            auth_user.verification_token = None
            auth_user.verification_token_expires_at = None
            self.db.commit()

    def update_email(self, user_id: str, new_email: str) -> str | None:
        """Update email, reset verification status, and return new verification token.

        Resets is_email_verified to False so the user must re-verify.
        """
        auth_user = self.get_by_user_id(user_id)
        if not auth_user:
            return None
        auth_user.email = new_email
        auth_user.is_email_verified = False
        auth_user.email_verified_at = None
        token = secrets.token_urlsafe(32)
        auth_user.verification_token = token
        auth_user.verification_token_expires_at = datetime.now(UTC) + timedelta(hours=24)
        self.db.commit()
        return token

    def set_verification_token(self, user_id: str, token: str, expires_hours: int = 24) -> None:
        """Set email verification token with expiration."""
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.verification_token = token
            auth_user.verification_token_expires_at = datetime.now(UTC) + timedelta(
                hours=expires_hours
            )
            self.db.commit()

    def set_reset_token(self, user_id: str, token: str, expires_hours: int = 1) -> None:
        """Set password reset token with expiration."""
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.reset_token = token
            auth_user.reset_token_expires_at = datetime.now(UTC) + timedelta(hours=expires_hours)
            self.db.commit()

    def clear_reset_token(self, user_id: str) -> None:
        """Clear password reset token after use."""
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.reset_token = None
            auth_user.reset_token_expires_at = None
            self.db.commit()

    def set_custom_password_flag(self, user_id: str, value: bool) -> None:
        """Set the has_custom_password flag for a user."""
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.has_custom_password = value
            self.db.commit()

    def update_password(self, user_id: str, password_hash: str) -> None:
        """Update user password hash."""
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.password_hash = password_hash
            auth_user.password_changed_at = datetime.now(UTC)
            self.db.commit()

    def increment_failed_login(self, user_id: str) -> int:
        """Increment failed login attempts. Locks account after 5 failures for 15 minutes."""
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.failed_login_attempts += 1

            if auth_user.failed_login_attempts >= 5:
                auth_user.locked_until = datetime.now(UTC) + timedelta(minutes=15)

            self.db.commit()
            return auth_user.failed_login_attempts
        return 0

    def reset_failed_login(self, user_id: str) -> None:
        """Reset failed login attempts after successful login."""
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.failed_login_attempts = 0
            auth_user.locked_until = None
            auth_user.last_login_at = datetime.now(UTC)
            self.db.commit()

    def update_last_login(self, user_id: str) -> None:
        """Update last login timestamp."""
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.last_login_at = datetime.now(UTC)
            self.db.commit()

    def soft_delete(self, user_id: str) -> None:
        """Soft delete auth user (30-day grace period)."""
        auth_user = self.get_by_user_id(user_id)
        if auth_user:
            auth_user.deleted_at = datetime.now(UTC)
            self.db.commit()

    def get_by_email_including_deleted(self, email: str) -> AuthUser | None:
        """Get auth user by email, including soft-deleted.

        Used for restoration detection during registration and login.
        """
        stmt = select(AuthUser).where(AuthUser.email == email)
        result = self.db.execute(stmt)
        return result.scalars().first()

    def get_by_restoration_token(self, token: str) -> AuthUser | None:
        """Get auth user by restoration token, including soft-deleted."""
        stmt = select(AuthUser).where(AuthUser.restoration_token == token)
        result = self.db.execute(stmt)
        return result.scalars().first()

    def set_restoration_token(self, user_id: str, token: str, expires_hours: int = 24) -> None:
        """Set account restoration token on a soft-deleted user.

        Queries without deleted_at filter since the target account is deleted.
        """
        stmt = select(AuthUser).where(AuthUser.user_id == user_id)
        result = self.db.execute(stmt)
        auth_user = result.scalars().first()
        if auth_user:
            auth_user.restoration_token = token
            auth_user.restoration_token_expires_at = datetime.now(UTC) + timedelta(
                hours=expires_hours
            )
            self.db.commit()

    def clear_restoration_token(self, user_id: str) -> None:
        """Clear restoration token after use.

        Queries without deleted_at filter since the target account may be deleted.
        """
        stmt = select(AuthUser).where(AuthUser.user_id == user_id)
        result = self.db.execute(stmt)
        auth_user = result.scalars().first()
        if auth_user:
            auth_user.restoration_token = None
            auth_user.restoration_token_expires_at = None
            self.db.commit()

    def restore_account(self, user_id: str) -> None:
        """Restore a soft-deleted account by clearing deleted_at."""
        stmt = select(AuthUser).where(AuthUser.user_id == user_id)
        result = self.db.execute(stmt)
        auth_user = result.scalars().first()
        if auth_user:
            auth_user.deleted_at = None
            self.db.commit()

    def get_expired_soft_deleted_users(self, retention_days: int) -> list[AuthUser]:
        """Get soft-deleted users whose grace period has expired."""
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        stmt = select(AuthUser).where(AuthUser.deleted_at.isnot(None), AuthUser.deleted_at < cutoff)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def get_all_soft_deleted_users(self, offset: int = 0, limit: int = 20) -> list[AuthUser]:
        """Get all soft-deleted users with pagination, ordered by deletion date."""
        stmt = (
            select(AuthUser)
            .where(AuthUser.deleted_at.isnot(None))
            .order_by(AuthUser.deleted_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def count_soft_deleted_users(self) -> int:
        """Count all soft-deleted users."""
        stmt = select(func.count()).select_from(AuthUser).where(AuthUser.deleted_at.isnot(None))
        result = self.db.execute(stmt)
        return result.scalar() or 0

    def hard_delete(self, user_id: str) -> bool:
        """Permanently delete auth user record."""
        stmt = select(AuthUser).where(AuthUser.user_id == user_id)
        result = self.db.execute(stmt)
        auth_user = result.scalars().first()
        if auth_user:
            self.db.delete(auth_user)
            self.db.commit()
            return True
        return False
