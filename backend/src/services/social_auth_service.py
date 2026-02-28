"""
Social Authentication Service

Business logic for OAuth 2.0 social login (Google, GitHub, etc.)
Implements Authorization Code Flow with PKCE for secure authentication.
"""

import base64
import hashlib
import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

import httpx  # noqa: F401 - used in verify_google_id_token; module-level needed for test patching
from authlib.integrations.httpx_client import OAuth2Client
from authlib.jose import jwt
from authlib.jose.errors import JoseError

from src.core.config import settings
from src.core.security import create_access_token, create_refresh_token, hash_password
from src.models.audit import AuditEventType, AuditOperation
from src.models.profile import AccountType
from src.repositories.auth_repository import AuthRepository
from src.repositories.profile_repository import ProfileRepository

if TYPE_CHECKING:
    from src.services.audit_service import AuditService


class OAuthProviderNotConfiguredError(Exception):
    """Raised when OAuth provider credentials are not configured."""

    pass


class OAuthStateValidationError(Exception):
    """Raised when OAuth state parameter validation fails (CSRF protection)."""

    pass


class OAuthTokenExchangeError(Exception):
    """Raised when token exchange with provider fails."""

    pass


class OAuthTokenVerificationError(Exception):
    """Raised when ID token verification fails."""

    pass


class AccountLinkingError(Exception):
    """Raised when account linking fails due to business logic violations."""

    pass


class SocialAuthService:
    """Service for OAuth 2.0 social authentication."""

    GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    GOOGLE_JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"
    GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"

    def __init__(
        self,
        auth_repo: AuthRepository,
        profile_repo: ProfileRepository,
        audit_service: Optional["AuditService"] = None,
    ):
        self.auth_repo = auth_repo
        self.profile_repo = profile_repo
        self.audit_service = audit_service

    def _audit(
        self,
        event_type: AuditEventType,
        user_id: UUID | None,
        resource_type: str,
        resource_id: str,
        operation: AuditOperation,
        changes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        legal_basis: str | None = None,
    ) -> None:
        """Log audit event if audit service available."""
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
                legal_basis=legal_basis,
            )

    def generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code_verifier and S256 code_challenge (RFC 7636)."""
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
        )
        challenge_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode("utf-8").rstrip("=")

        return code_verifier, code_challenge

    def generate_authorization_url(
        self, provider: str, state: str | None = None
    ) -> tuple[str, str, str]:
        """Generate OAuth authorization URL with PKCE.

        Returns:
            Tuple of (authorization_url, state, code_verifier)
        """
        if provider != "google":
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise OAuthProviderNotConfiguredError(
                "Google OAuth credentials not configured."
                " Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
            )

        if not state:
            state = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")

        code_verifier, code_challenge = self.generate_pkce_pair()

        client = OAuth2Client(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )

        authorization_url, _ = client.create_authorization_url(
            url=self.GOOGLE_AUTHORIZATION_ENDPOINT,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method="S256",
            scope="openid email profile",
            access_type="offline",
            prompt="consent",
        )

        return authorization_url, state, code_verifier

    def exchange_code_for_token(
        self, provider: str, code: str, code_verifier: str, state: str, expected_state: str
    ) -> dict[str, Any]:
        """Exchange authorization code for tokens, validating state for CSRF protection."""
        if provider != "google":
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        if state != expected_state:
            raise OAuthStateValidationError("State parameter mismatch. Possible CSRF attack.")

        client = OAuth2Client(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )

        try:
            token_response = client.fetch_token(
                url=self.GOOGLE_TOKEN_ENDPOINT,
                grant_type="authorization_code",
                code=code,
                code_verifier=code_verifier,
            )

            return token_response
        except Exception as e:
            raise OAuthTokenExchangeError(f"Failed to exchange authorization code: {str(e)}")

    def verify_google_id_token(self, id_token: str) -> dict[str, Any]:
        """Verify and decode a Google ID token against Google JWKS."""
        try:
            import httpx

            jwks_response = httpx.get(self.GOOGLE_JWKS_URI, timeout=10.0)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()

            claims = jwt.decode(
                id_token,
                jwks,
                claims_options={
                    "iss": {
                        "essential": True,
                        "values": ["https://accounts.google.com", "accounts.google.com"],
                    },
                    "aud": {"essential": True, "value": settings.GOOGLE_CLIENT_ID},
                },
            )

            if "sub" not in claims or "email" not in claims:
                raise OAuthTokenVerificationError("Missing required claims in ID token")

            return claims

        except JoseError as e:
            raise OAuthTokenVerificationError(f"ID token verification failed: {str(e)}")
        except Exception as e:
            raise OAuthTokenVerificationError(f"Unexpected error verifying ID token: {str(e)}")

    def authenticate_or_create_user(
        self,
        provider: str,
        provider_id: str,
        email: str,
        display_name: str,
        email_verified: bool = False,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str, str, bool, str, bool, bool, str, bool]:
        """Authenticate existing OAuth user or create a new account.

        Returns:
            Tuple of (access_token, refresh_token, user_id, is_new_user,
                       account_type, is_email_verified, is_admin, provider,
                       has_custom_password)
        """
        existing_oauth_user = self.auth_repo.get_by_provider(provider, provider_id)

        if existing_oauth_user:
            user_id_str = str(existing_oauth_user.user_id)
            profile = self.profile_repo.get_profile_by_id(UUID(user_id_str))
            account_type = profile.account_type.value if profile else "unverified"

            from src.core.config import settings

            is_admin = existing_oauth_user.is_admin or email.lower() in settings.admin_emails

            self.auth_repo.update_last_login(UUID(user_id_str))

            access_token = create_access_token(
                user_id=user_id_str, email=email, account_type=account_type, is_admin=is_admin
            )
            refresh_token = create_refresh_token(user_id=user_id_str)

            self._audit(
                event_type=AuditEventType.login_success,
                user_id=UUID(user_id_str),
                resource_type="auth_user",
                resource_id=user_id_str,
                operation=AuditOperation.login,
                ip_address=ip_address,
                user_agent=user_agent,
                legal_basis="Performance of contract (Art. 6(1)(b) GDPR)",
            )

            return (
                access_token,
                refresh_token,
                user_id_str,
                False,
                account_type,
                existing_oauth_user.is_email_verified,
                is_admin,
                provider,
                existing_oauth_user.has_custom_password,
            )

        deleted_oauth_user = self.auth_repo.get_by_provider_including_deleted(provider, provider_id)
        if deleted_oauth_user and deleted_oauth_user.deleted_at is not None:
            from datetime import timedelta

            from src.core.config import settings

            retention_days = settings.DELETION_RETENTION_DAYS
            deleted_at = deleted_oauth_user.deleted_at
            if deleted_at.tzinfo is None:
                deleted_at = deleted_at.replace(tzinfo=UTC)

            permanent_date = deleted_at + timedelta(days=retention_days)

            if permanent_date > datetime.now(UTC):
                raise AccountLinkingError(
                    f"Account for {provider} user {provider_id}"
                    f" was deleted on {deleted_at.isoformat()}. "
                    f"ACCOUNT_RECOVERABLE|{permanent_date.isoformat()}"
                )
            else:
                old_user_id = str(deleted_oauth_user.user_id)
                self.profile_repo.hard_delete_profile(UUID(old_user_id))
                self.auth_repo.hard_delete(old_user_id)

        existing_email_user = self.auth_repo.get_by_email(email)

        if existing_email_user:
            raise AccountLinkingError(
                f"Email {email} already registered with email/password authentication. "
                "Account linking not yet implemented. Please login with your password."
            )

        # Account type starts unverified; only admin document review promotes to verified
        account_type = AccountType.unverified

        profile = self.profile_repo.create_profile(
            account_type=account_type,
            primary_email=email,
            preferred_language="en",
        )

        user_id_str = str(profile.user_id)

        # OAuth users get a random password hash for schema compatibility
        random_password_hash = hash_password(secrets.token_urlsafe(32))

        from src.core.config import settings

        is_admin = email.lower() in settings.admin_emails

        self.auth_repo.create_user(
            user_id=user_id_str,
            email=email,
            password_hash=random_password_hash,
            is_email_verified=email_verified,
            provider=provider,
            provider_id=provider_id,
        )

        access_token = create_access_token(
            user_id=user_id_str, email=email, account_type=account_type.value, is_admin=is_admin
        )
        refresh_token = create_refresh_token(user_id=user_id_str)

        self._audit(
            event_type=AuditEventType.register,
            user_id=UUID(user_id_str),
            resource_type="auth_user",
            resource_id=user_id_str,
            operation=AuditOperation.create,
            changes={"provider": provider, "email": email, "is_email_verified": email_verified},
            ip_address=ip_address,
            user_agent=user_agent,
            legal_basis="Performance of contract (Art. 6(1)(b) GDPR)",
        )

        return (
            access_token,
            refresh_token,
            user_id_str,
            True,
            account_type.value,
            email_verified,
            is_admin,
            provider,
            False,
        )
