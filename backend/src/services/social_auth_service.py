"""
Social Authentication Service

Business logic for OAuth 2.0 social login (Google, GitHub, etc.)
Implements Authorization Code Flow with PKCE for secure authentication.
"""

import secrets
import hashlib
import base64
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from uuid import UUID, uuid4

from authlib.integrations.httpx_client import OAuth2Client
from authlib.jose import jwt
from authlib.jose.errors import JoseError

from src.repositories.auth_repository import AuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.core.config import settings
from src.core.security import create_access_token, create_refresh_token, hash_password
from src.models.profile import AccountType
from src.models.audit import AuditEventType, AuditOperation

# Type checking to avoid circular import
from typing import TYPE_CHECKING
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

    # Google OAuth endpoints
    GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    GOOGLE_JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"
    GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"

    def __init__(
        self,
        auth_repo: AuthRepository,
        profile_repo: ProfileRepository,
        audit_service: Optional["AuditService"] = None
    ):
        """
        Initialize social auth service.

        Args:
            auth_repo: Authentication repository
            profile_repo: Profile repository
            audit_service: Optional audit service for logging
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
                legal_basis=legal_basis
            )

    def generate_pkce_pair(self) -> Tuple[str, str]:
        """
        Generate PKCE code_verifier and code_challenge.

        Returns:
            Tuple of (code_verifier, code_challenge)

        PKCE (RFC 7636) protects authorization code from interception attacks.
        Uses S256 challenge method (SHA-256 hash of verifier).
        """
        # Generate cryptographically random code_verifier (43-128 chars)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

        # Generate code_challenge = BASE64URL(SHA256(code_verifier))
        challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')

        return code_verifier, code_challenge

    def generate_authorization_url(
        self,
        provider: str,
        state: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Generate OAuth authorization URL with PKCE.

        Args:
            provider: OAuth provider name ('google')
            state: Optional state parameter (generated if not provided)

        Returns:
            Tuple of (authorization_url, state, code_verifier)

        Raises:
            OAuthProviderNotConfiguredError: If provider credentials not configured
            ValueError: If provider not supported
        """
        if provider != "google":
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        # Validate Google OAuth configuration
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise OAuthProviderNotConfiguredError(
                "Google OAuth credentials not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
            )

        # Generate CSRF protection state if not provided
        if not state:
            state = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

        # Generate PKCE pair
        code_verifier, code_challenge = self.generate_pkce_pair()

        # Create OAuth client
        client = OAuth2Client(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )

        # Generate authorization URL with PKCE parameters
        authorization_url, _ = client.create_authorization_url(
            url=self.GOOGLE_AUTHORIZATION_ENDPOINT,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method="S256",
            scope="openid email profile",
            access_type="offline",  # Request refresh token
            prompt="consent"  # Force consent screen for refresh token
        )

        return authorization_url, state, code_verifier

    def exchange_code_for_token(
        self,
        provider: str,
        code: str,
        code_verifier: str,
        state: str,
        expected_state: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token and ID token.

        Args:
            provider: OAuth provider name ('google')
            code: Authorization code from provider
            code_verifier: PKCE code verifier
            state: State parameter from callback
            expected_state: Expected state value (CSRF protection)

        Returns:
            Token response with access_token, id_token, etc.

        Raises:
            OAuthStateValidationError: If state validation fails
            OAuthTokenExchangeError: If token exchange fails
            ValueError: If provider not supported
        """
        if provider != "google":
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        # Validate state parameter (CSRF protection)
        if state != expected_state:
            raise OAuthStateValidationError("State parameter mismatch. Possible CSRF attack.")

        # Create OAuth client
        client = OAuth2Client(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )

        try:
            # Exchange authorization code for tokens
            # PKCE: code_verifier must be passed to fetch_token(), not OAuth2Client constructor
            token_response = client.fetch_token(
                url=self.GOOGLE_TOKEN_ENDPOINT,
                grant_type="authorization_code",
                code=code,
                code_verifier=code_verifier  # Include PKCE verifier in token exchange
            )

            return token_response
        except Exception as e:
            raise OAuthTokenExchangeError(f"Failed to exchange authorization code: {str(e)}")

    def verify_google_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        Verify and decode Google ID token (JWT).

        Args:
            id_token: Google ID token (JWT)

        Returns:
            Decoded token claims

        Raises:
            OAuthTokenVerificationError: If token verification fails
        """
        try:
            # Fetch Google's public keys (JWKS)
            # In production, cache these keys with TTL
            import httpx
            jwks_response = httpx.get(self.GOOGLE_JWKS_URI, timeout=10.0)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()

            # Verify and decode ID token
            claims = jwt.decode(
                id_token,
                jwks,
                claims_options={
                    "iss": {"essential": True, "values": ["https://accounts.google.com", "accounts.google.com"]},
                    "aud": {"essential": True, "value": settings.GOOGLE_CLIENT_ID}
                }
            )

            # Validate required claims
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
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[str, str, str, bool, str, bool, bool, str, bool]:
        """
        Authenticate existing OAuth user or create new account.

        Implements account linking logic:
        - If OAuth account exists (provider + provider_id match), authenticate
        - If email matches existing email/password account, this is account linking
          (requires explicit user consent in future implementation)
        - Otherwise, create new account with OAuth credentials

        Args:
            provider: OAuth provider name
            provider_id: Provider-specific user identifier
            email: User email from provider
            display_name: User display name from provider
            email_verified: Email verification status from provider
            ip_address: Optional client IP for audit
            user_agent: Optional user agent for audit

        Returns:
            Tuple of (access_token, refresh_token, user_id, is_new_user, account_type,
                       is_email_verified, is_admin, provider, has_custom_password)

        Raises:
            AccountLinkingError: If account linking fails
        """
        # Check if OAuth account already exists (active accounts only)
        existing_oauth_user = self.auth_repo.get_by_provider(provider, provider_id)

        if existing_oauth_user:
            # Existing OAuth user - authenticate directly
            user_id_str = str(existing_oauth_user.user_id)

            # Get profile for account_type
            profile = self.profile_repo.get_profile_by_id(UUID(user_id_str))
            account_type = profile.account_type.value if profile else "unverified"

            # Get admin status (check DB flag + ADMIN_USER_EMAILS fallback)
            from src.core.config import settings
            is_admin = existing_oauth_user.is_admin or email.lower() in settings.admin_emails

            # Update last login timestamp
            self.auth_repo.update_last_login(UUID(user_id_str))

            # Issue JWT tokens
            access_token = create_access_token(user_id=user_id_str, email=email, account_type=account_type, is_admin=is_admin)
            refresh_token = create_refresh_token(user_id=user_id_str)

            # Audit login event
            self._audit(
                event_type=AuditEventType.login_success,
                user_id=UUID(user_id_str),
                resource_type="auth_user",
                resource_id=user_id_str,
                operation=AuditOperation.login,
                ip_address=ip_address,
                user_agent=user_agent,
                legal_basis="Performance of contract (Art. 6(1)(b) GDPR)"
            )

            return access_token, refresh_token, user_id_str, False, account_type, existing_oauth_user.is_email_verified, is_admin, provider, existing_oauth_user.has_custom_password

        # Check for soft-deleted OAuth account (restoration needed)
        deleted_oauth_user = self.auth_repo.get_by_provider_including_deleted(provider, provider_id)
        if deleted_oauth_user and deleted_oauth_user.deleted_at is not None:
            from src.core.config import settings
            from datetime import timedelta

            retention_days = settings.DELETION_RETENTION_DAYS
            deleted_at = deleted_oauth_user.deleted_at
            if deleted_at.tzinfo is None:
                deleted_at = deleted_at.replace(tzinfo=timezone.utc)

            permanent_date = deleted_at + timedelta(days=retention_days)

            # Only offer restoration if within grace period
            if permanent_date > datetime.now(timezone.utc):
                raise AccountLinkingError(
                    f"Account for {provider} user {provider_id} was deleted on {deleted_at.isoformat()}. "
                    f"ACCOUNT_RECOVERABLE|{permanent_date.isoformat()}"
                )
            else:
                # Grace period expired: purge the old account so re-registration
                # can proceed. Order follows privacy_service.purge_expired_accounts:
                # hard-delete profile first (CASCADE handles children), then auth_user.
                old_user_id = str(deleted_oauth_user.user_id)
                self.profile_repo.hard_delete_profile(UUID(old_user_id))
                self.auth_repo.hard_delete(old_user_id)

        # Check if email already exists (potential account linking)
        existing_email_user = self.auth_repo.get_by_email(email)

        if existing_email_user:
            # Account linking scenario: email exists but not linked to this OAuth provider
            # For MVP, we'll reject this and require manual account linking
            # In production, implement explicit consent flow
            raise AccountLinkingError(
                f"Email {email} already registered with email/password authentication. "
                "Account linking not yet implemented. Please login with your password."
            )

        # Create new user with OAuth credentials
        # Account type starts as unverified regardless of email verification.
        # Email verification (tracked by auth_users.is_email_verified) and
        # identity verification (account_type=verified via admin document
        # review) are separate concerns. Only admin approval of a government
        # ID document promotes account_type to verified.
        account_type = AccountType.unverified

        # Create base profile first
        # Note: BaseProfile model will auto-generate user_id
        profile = self.profile_repo.create_profile(
            account_type=account_type,
            primary_email=email,
            preferred_language="en",
        )

        # Get the generated user_id and ensure it's a string
        user_id_str = str(profile.user_id)

        # Create auth_user with OAuth credentials
        # OAuth users don't have passwords, but we hash a random token for schema compatibility
        random_password_hash = hash_password(secrets.token_urlsafe(32))

        # Check if user should be admin (from ADMIN_USER_EMAILS)
        from src.core.config import settings
        is_admin = email.lower() in settings.admin_emails

        self.auth_repo.create_user(
            user_id=user_id_str,
            email=email,
            password_hash=random_password_hash,  # Not used for OAuth users
            is_email_verified=email_verified,
            provider=provider,
            provider_id=provider_id
        )

        # Issue JWT tokens with admin status
        access_token = create_access_token(user_id=user_id_str, email=email, account_type=account_type.value, is_admin=is_admin)
        refresh_token = create_refresh_token(user_id=user_id_str)

        # Audit account creation
        self._audit(
            event_type=AuditEventType.register,
            user_id=UUID(user_id_str),
            resource_type="auth_user",
            resource_id=user_id_str,
            operation=AuditOperation.create,
            changes={
                "provider": provider,
                "email": email,
                "is_email_verified": email_verified
            },
            ip_address=ip_address,
            user_agent=user_agent,
            legal_basis="Performance of contract (Art. 6(1)(b) GDPR)"
        )

        return access_token, refresh_token, user_id_str, True, account_type.value, email_verified, is_admin, provider, False
