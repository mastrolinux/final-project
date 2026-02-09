"""
Authentication Service

Business logic layer for authentication operations.
Handles user registration, login, email verification, and password reset.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple, TYPE_CHECKING
import secrets
from uuid import UUID

from src.repositories.auth_repository import AuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.core.config import settings
from src.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    verify_token
)
from src.tasks.email_tasks import (
    send_verification_email,
    send_password_reset_email,
    send_restoration_email,
)
from src.models.audit import AuditEventType, AuditOperation

if TYPE_CHECKING:
    from src.services.audit_service import AuditService


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware UTC.

    SQLite stores timestamps without timezone info. PostgreSQL preserves it.
    This helper normalizes both cases to UTC-aware datetimes.
    """
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AuthService:
    """Service for authentication operations."""

    def __init__(
        self,
        auth_repo: AuthRepository,
        profile_repo: ProfileRepository,
        audit_service: Optional["AuditService"] = None
    ):
        """
        Initialize auth service with repositories.

        Args:
            auth_repo: Authentication repository
            profile_repo: Profile repository (to get account_type)
            audit_service: Optional audit service for event logging
        """
        self.auth_repo = auth_repo
        self.profile_repo = profile_repo
        self.audit_service = audit_service

    def _audit(
        self,
        event_type: AuditEventType,
        user_id: Optional[UUID],
        resource_type: str,
        resource_id: str,
        operation: AuditOperation,
        changes: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        legal_basis: Optional[str] = None
    ) -> None:
        """Helper to log audit events if audit_service is available."""
        if self.audit_service:
            self.audit_service.log_event(
                event_type=event_type,
                user_id=user_id,
                actor_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                operation=operation,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
                legal_basis=legal_basis
            )

    def register_user(
        self,
        email: str,
        password: str,
        user_id: str,
        display_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Register new user with email and password.

        Process:
        1. Check if email already exists
        2. Validate password strength
        3. Hash password with Argon2id
        4. Create auth_users record
        5. Generate verification token
        6. Send verification email (async via Celery)

        Args:
            email: User email address
            password: Plain text password
            user_id: User ID from base_profiles (must exist)
            display_name: User's display name for email personalization
            ip_address: Client IP address (for audit logging)
            user_agent: Client user agent (for audit logging)

        Returns:
            Tuple of (success, error_message, auth_data)
            auth_data contains: user_id, email, is_email_verified
        """
        # Check if email already exists (active accounts)
        existing = self.auth_repo.get_by_email(email)
        if existing:
            return False, "Email already registered", None

        # Check for soft-deleted recoverable account
        deleted_user = self.auth_repo.get_by_email_including_deleted(email)
        if deleted_user and deleted_user.deleted_at is not None:
            from src.core.config import settings
            from datetime import timedelta
            retention_days = settings.DELETION_RETENTION_DAYS
            deleted_at = _ensure_utc(deleted_user.deleted_at)
            permanent_date = deleted_at + timedelta(days=retention_days)
            now = datetime.now(timezone.utc)
            if permanent_date > now:
                # Account is recoverable
                return False, "ACCOUNT_RECOVERABLE", {
                    "account_recoverable": True,
                    "permanent_deletion_date": permanent_date.isoformat(),
                    "restore_endpoint": "/api/v1/auth/restore-account",
                }
            # Grace period expired, allow fresh registration

        # Validate password strength
        valid, message = validate_password_strength(password)
        if not valid:
            return False, message, None

        # Hash password with Argon2id
        password_hash = hash_password(password)

        # Create auth user
        auth_user = self.auth_repo.create(email, password_hash, user_id)

        # Generate secure verification token
        verification_token = secrets.token_urlsafe(32)
        self.auth_repo.set_verification_token(user_id, verification_token, expires_hours=24)

        # Send verification email asynchronously
        send_verification_email.delay(email, verification_token, display_name)

        # Audit: registration
        self._audit(
            event_type=AuditEventType.register,
            user_id=UUID(user_id),
            resource_type="auth_user",
            resource_id=user_id,
            operation=AuditOperation.register,
            changes={"email": email},
            ip_address=ip_address,
            user_agent=user_agent,
            legal_basis="contract"
        )

        return True, None, {
            "user_id": str(auth_user.user_id),
            "email": auth_user.email,
            "is_email_verified": False,
            "message": "Registration successful. Please check your email to verify your account."
        }

    def login(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Authenticate user and return JWT tokens.

        Process:
        1. Get auth user by email
        2. Check if account is locked
        3. Verify password
        4. Reset failed login attempts on success
        5. Get account type from base_profiles
        6. Generate access and refresh tokens

        Args:
            email: User email address
            password: Plain text password
            ip_address: Client IP address (for audit logging)
            user_agent: Client user agent (for audit logging)

        Returns:
            Tuple of (success, error_message, token_data)
            token_data contains: access_token, refresh_token, token_type, expires_in, user_id, email
        """
        # Get auth user (active accounts only)
        auth_user = self.auth_repo.get_by_email(email)
        if not auth_user:
            # Check for soft-deleted account
            deleted_user = self.auth_repo.get_by_email_including_deleted(email)
            if deleted_user and deleted_user.deleted_at is not None:
                from datetime import timedelta
                retention_days = settings.DELETION_RETENTION_DAYS
                deleted_at = _ensure_utc(deleted_user.deleted_at)
                permanent_date = deleted_at + timedelta(
                    days=retention_days
                )
                if permanent_date > datetime.now(timezone.utc):
                    return False, "ACCOUNT_DELETED", {
                        "deletion_scheduled_at": deleted_user.deleted_at.isoformat(),
                        "permanent_deletion_date": permanent_date.isoformat(),
                        "recovery_info": (
                            "Register again with the same email to restore "
                            "your account before the permanent deletion date."
                        ),
                    }
            return False, "Invalid email or password", None

        # Check if account is locked
        if auth_user.is_locked():
            # Audit: account lock
            self._audit(
                event_type=AuditEventType.account_lock,
                user_id=auth_user.user_id,
                resource_type="auth_user",
                resource_id=str(auth_user.user_id),
                operation=AuditOperation.login,
                changes={"reason": "account_locked"},
                ip_address=ip_address,
                user_agent=user_agent,
                legal_basis="legitimate_interest"
            )
            return False, "Account temporarily locked due to failed login attempts. Please try again later.", None

        # Verify password
        if not verify_password(password, auth_user.password_hash):
            # Increment failed login attempts
            self.auth_repo.increment_failed_login(str(auth_user.user_id))

            # Audit: login failure
            self._audit(
                event_type=AuditEventType.login_failure,
                user_id=auth_user.user_id,
                resource_type="auth_user",
                resource_id=str(auth_user.user_id),
                operation=AuditOperation.login,
                changes={"reason": "invalid_password"},
                ip_address=ip_address,
                user_agent=user_agent,
                legal_basis="legitimate_interest"
            )
            return False, "Invalid email or password", None

        # Reset failed login attempts on successful login
        self.auth_repo.reset_failed_login(str(auth_user.user_id))

        # Get account type from base_profiles
        base_profile = self.profile_repo.get_profile_by_id(auth_user.user_id)
        account_type = base_profile.account_type.value if base_profile else "unverified"

        # Generate JWT tokens
        access_token = create_access_token(
            str(auth_user.user_id),
            auth_user.email,
            account_type
        )
        refresh_token = create_refresh_token(str(auth_user.user_id))

        # Check admin status from database OR environment config
        is_admin = auth_user.is_admin or (
            auth_user.email.lower() in settings.admin_emails
        )

        # Audit: login success
        self._audit(
            event_type=AuditEventType.login_success,
            user_id=auth_user.user_id,
            resource_type="auth_user",
            resource_id=str(auth_user.user_id),
            operation=AuditOperation.login,
            ip_address=ip_address,
            user_agent=user_agent,
            legal_basis="contract"
        )

        return True, None, {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600,  # 1 hour
            "user_id": str(auth_user.user_id),
            "email": auth_user.email,
            "is_email_verified": auth_user.is_email_verified,
            "account_type": account_type,
            "is_admin": is_admin
        }

    def verify_email(self, token: str) -> Tuple[bool, Optional[str]]:
        """
        Verify email with verification token.

        Process:
        1. Find auth user by verification token
        2. Check if token exists and not expired
        3. Update verification status
        4. Clear verification token

        Args:
            token: Email verification token

        Returns:
            Tuple of (success, error_message)
        """
        # Find auth user by verification token
        auth_user = self.auth_repo.get_by_verification_token(token)
        if not auth_user:
            return False, "Invalid or expired verification token"

        # Check if token is valid and not expired
        if not auth_user.is_verification_token_valid(token):
            return False, "Verification token has expired. Please request a new one."

        # Update verification status
        self.auth_repo.update_verification_status(str(auth_user.user_id), verified=True)

        # Audit: email verification
        self._audit(
            event_type=AuditEventType.email_verification,
            user_id=auth_user.user_id,
            resource_type="auth_user",
            resource_id=str(auth_user.user_id),
            operation=AuditOperation.verify,
            legal_basis="contract"
        )

        return True, None

    def request_password_reset(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Request password reset email.

        Process:
        1. Find auth user by email
        2. Generate secure reset token
        3. Store token with 1-hour expiry
        4. Send reset email (async via Celery)

        Note: Always returns success even if email doesn't exist (security best practice)

        Args:
            email: User email address

        Returns:
            Tuple of (success, error_message)
        """
        # Get auth user
        auth_user = self.auth_repo.get_by_email(email)
        if not auth_user:
            # Return success even if email doesn't exist (prevent email enumeration)
            return True, None

        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)
        self.auth_repo.set_reset_token(str(auth_user.user_id), reset_token, expires_hours=1)

        # Send reset email asynchronously
        send_password_reset_email.delay(email, reset_token)

        # Audit: password reset request
        self._audit(
            event_type=AuditEventType.password_reset_request,
            user_id=auth_user.user_id,
            resource_type="auth_user",
            resource_id=str(auth_user.user_id),
            operation=AuditOperation.update,
            legal_basis="contract"
        )

        return True, None

    def reset_password(
        self,
        token: str,
        new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Reset password with reset token.

        Process:
        1. Find auth user by reset token
        2. Check if token is valid and not expired
        3. Validate new password strength
        4. Hash new password
        5. Update password hash
        6. Clear reset token

        Args:
            token: Password reset token
            new_password: New plain text password

        Returns:
            Tuple of (success, error_message)
        """
        # Find auth user by reset token
        auth_user = self.auth_repo.get_by_reset_token(token)
        if not auth_user:
            return False, "Invalid or expired reset token"

        # Check if token is valid and not expired
        if not auth_user.is_reset_token_valid(token):
            return False, "Reset token has expired. Please request a new one."

        # Validate new password strength
        valid, message = validate_password_strength(new_password)
        if not valid:
            return False, message

        # Hash new password
        password_hash = hash_password(new_password)

        # Update password and clear reset token
        self.auth_repo.update_password(str(auth_user.user_id), password_hash)
        self.auth_repo.clear_reset_token(str(auth_user.user_id))

        # Audit: password reset
        self._audit(
            event_type=AuditEventType.password_reset,
            user_id=auth_user.user_id,
            resource_type="auth_user",
            resource_id=str(auth_user.user_id),
            operation=AuditOperation.update,
            legal_basis="contract"
        )

        return True, None

    def resend_verification_email(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Resend verification email to user.

        Process:
        1. Find auth user by email
        2. Check if already verified
        3. Generate new verification token
        4. Send verification email

        Args:
            email: User email address

        Returns:
            Tuple of (success, error_message)
        """
        # Get auth user
        auth_user = self.auth_repo.get_by_email(email)
        if not auth_user:
            return False, "Email not found"

        # Check if already verified
        if auth_user.is_email_verified:
            return False, "Email is already verified"

        # Get user's display name from base_profiles
        base_profile = self.profile_repo.get_profile_by_id(auth_user.user_id)
        display_name = "User" if not base_profile else (base_profile.legal_name or "User")

        # Generate new verification token
        verification_token = secrets.token_urlsafe(32)
        self.auth_repo.set_verification_token(str(auth_user.user_id), verification_token, expires_hours=24)

        # Send verification email asynchronously
        send_verification_email.delay(email, verification_token, display_name)

        return True, None

    def refresh_access_token(
        self,
        refresh_token: str,
        blacklist: "TokenBlacklist"
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Exchange valid refresh token for new access and refresh tokens.

        Implements refresh token rotation: the old refresh token is blacklisted
        and new tokens are issued. This limits the impact of token theft.

        Process:
            1. Verify refresh token signature and type
            2. Check JTI against Redis blacklist
            3. Get user from database, validate account status
            4. Blacklist old token JTI (before issuing new tokens)
            5. Generate new access + refresh tokens

        Args:
            refresh_token: JWT refresh token from client
            blacklist: TokenBlacklist instance for rotation

        Returns:
            Tuple of (success, error_code, token_data)
            token_data contains: access_token, refresh_token, token_type, expires_in

        Error codes:
            INVALID_TOKEN: Signature invalid, expired, or wrong type
            REVOKED_TOKEN: Token was previously used (blacklisted)
            USER_NOT_FOUND: User ID from token not in database
            ACCOUNT_LOCKED: Account temporarily locked
            ACCOUNT_DELETED: Account soft deleted
            SERVICE_UNAVAILABLE: Redis blacklist unavailable
        """
        from redis.exceptions import ConnectionError as RedisConnectionError

        # Step 1: Verify refresh token signature and type
        token_data = verify_token(refresh_token, token_type="refresh")
        if token_data is None:
            return False, "INVALID_TOKEN", None

        # Step 2: Check if token is blacklisted (revoked)
        try:
            if blacklist.is_blacklisted(token_data.jti):
                return False, "REVOKED_TOKEN", None
        except RedisConnectionError:
            return False, "SERVICE_UNAVAILABLE", None

        # Step 3: Get user from database
        auth_user = self.auth_repo.get_by_user_id(token_data.user_id)
        if auth_user is None:
            return False, "USER_NOT_FOUND", None

        # Step 4: Validate account status
        if auth_user.deleted_at is not None:
            return False, "ACCOUNT_DELETED", None

        if auth_user.is_locked():
            return False, "ACCOUNT_LOCKED", None

        # Step 5: Blacklist old token BEFORE issuing new tokens
        # Calculate TTL: use remaining time until token expiry
        now = datetime.now(timezone.utc)
        token_exp = token_data.exp
        if token_exp.tzinfo is None:
            token_exp = token_exp.replace(tzinfo=timezone.utc)

        remaining_ttl = int((token_exp - now).total_seconds())
        if remaining_ttl > 0:
            try:
                blacklist.blacklist_token(token_data.jti, remaining_ttl)
            except RedisConnectionError:
                return False, "SERVICE_UNAVAILABLE", None

        # Step 6: Get account type from base_profiles
        base_profile = self.profile_repo.get_profile_by_id(auth_user.user_id)
        account_type = base_profile.account_type.value if base_profile else "unverified"

        # Step 7: Generate new tokens
        new_access_token = create_access_token(
            str(auth_user.user_id),
            auth_user.email,
            account_type
        )
        new_refresh_token = create_refresh_token(str(auth_user.user_id))

        return True, None, {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": 3600  # 1 hour
        }

    def request_account_restoration(
        self,
        email: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Request account restoration after soft deletion.

        Generates a time-limited restoration token and sends it via email.
        Always returns success to prevent email enumeration.

        Args:
            email: Email of the soft-deleted account

        Returns:
            Tuple of (success, error_message)
        """
        from datetime import timedelta

        # Look for soft-deleted account
        auth_user = self.auth_repo.get_by_email_including_deleted(email)
        if not auth_user or auth_user.deleted_at is None:
            # No soft-deleted account found, but return success anyway
            return True, None

        # Check if grace period has expired
        retention_days = settings.DELETION_RETENTION_DAYS
        deleted_at = _ensure_utc(auth_user.deleted_at)
        permanent_date = deleted_at + timedelta(days=retention_days)
        if permanent_date <= datetime.now(timezone.utc):
            # Grace period expired, return success without sending email
            return True, None

        # Generate restoration token
        restoration_token = secrets.token_urlsafe(32)
        self.auth_repo.set_restoration_token(
            str(auth_user.user_id), restoration_token, expires_hours=24
        )

        # Send restoration email
        send_restoration_email.delay(email, restoration_token)

        return True, None

    def confirm_account_restoration(
        self,
        token: str,
        new_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Confirm account restoration with token and new password.

        Validates the restoration token, checks grace period, restores all
        user records, sets new password, and issues JWT tokens.

        Args:
            token: Restoration token from email
            new_password: New password for the restored account
            ip_address: Client IP address (for audit logging)
            user_agent: Client user agent (for audit logging)

        Returns:
            Tuple of (success, error_code, data)
            error_code is one of: INVALID_RESTORATION_TOKEN, ACCOUNT_PERMANENTLY_DELETED
        """
        from datetime import timedelta

        # Find user by restoration token (including deleted accounts)
        auth_user = self.auth_repo.get_by_restoration_token(token)
        if not auth_user:
            return False, "INVALID_RESTORATION_TOKEN", None

        # Validate token expiry
        if not auth_user.is_restoration_token_valid(token):
            return False, "INVALID_RESTORATION_TOKEN", None

        # Check grace period
        retention_days = settings.DELETION_RETENTION_DAYS
        deleted_at = _ensure_utc(auth_user.deleted_at)
        if deleted_at is None:
            # Account already restored or was never deleted
            return False, "INVALID_RESTORATION_TOKEN", None
        permanent_date = deleted_at + timedelta(days=retention_days)
        if permanent_date <= datetime.now(timezone.utc):
            return False, "ACCOUNT_PERMANENTLY_DELETED", None

        # Validate new password strength
        valid, message = validate_password_strength(new_password)
        if not valid:
            return False, message, None

        # Hash new password
        password_hash = hash_password(new_password)

        # Restore auth user (clear deleted_at)
        self.auth_repo.restore_account(str(auth_user.user_id))

        # Restore base profile
        self.profile_repo.restore_profile(auth_user.user_id)

        # Restore context profiles
        from src.repositories.context_repository import ContextRepository
        # Access context repo if available through the profile_repo's db session
        context_repo = ContextRepository(self.auth_repo.db)
        context_repo.restore_user_contexts(auth_user.user_id)

        # Set new password
        self.auth_repo.update_password(str(auth_user.user_id), password_hash)

        # Clear restoration token
        self.auth_repo.clear_restoration_token(str(auth_user.user_id))

        # Get account type for token generation
        base_profile = self.profile_repo.get_profile_by_id(auth_user.user_id)
        account_type = (
            base_profile.account_type.value if base_profile else "unverified"
        )

        # Generate new JWT tokens
        access_token = create_access_token(
            str(auth_user.user_id),
            auth_user.email,
            account_type
        )
        refresh_token_val = create_refresh_token(str(auth_user.user_id))

        now = datetime.now(timezone.utc)

        # Audit: account restoration
        self._audit(
            event_type=AuditEventType.account_restored,
            user_id=auth_user.user_id,
            resource_type="account",
            resource_id=str(auth_user.user_id),
            operation=AuditOperation.restore,
            changes={"restored_at": now.isoformat()},
            ip_address=ip_address,
            user_agent=user_agent,
            legal_basis="contract"
        )

        return True, None, {
            "message": "Account restored successfully",
            "access_token": access_token,
            "refresh_token": refresh_token_val,
            "token_type": "bearer",
            "restored_at": now.isoformat(),
        }
