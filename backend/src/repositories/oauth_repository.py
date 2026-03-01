"""
OAuth Repository

Data access layer for OAuth 2.1 entities.
Handles database operations for clients, tokens, and consents.
"""

import hashlib
import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.models.oauth import (
    OAuthAccessToken,
    OAuthAuthorizationCode,
    OAuthClient,
    OAuthConsent,
    OAuthRefreshToken,
    OAuthScope,
)


class OAuthRepository:
    """Repository for OAuth data access operations"""

    def __init__(self, db: Session):
        self.db = db

    #
    # Scope Operations
    #

    def get_scope(self, scope_name: str) -> OAuthScope | None:
        """Get a scope by name"""
        return self.db.query(OAuthScope).filter(OAuthScope.scope_name == scope_name).first()

    def get_scopes(self, scope_names: list[str]) -> list[OAuthScope]:
        """Get multiple scopes by name"""
        return self.db.query(OAuthScope).filter(OAuthScope.scope_name.in_(scope_names)).all()

    def list_all_scopes(self) -> list[OAuthScope]:
        """List all available scopes"""
        return self.db.query(OAuthScope).all()

    #
    # Client Operations
    #

    def get_client(self, client_id: str) -> OAuthClient | None:
        """Get a client by ID"""
        return (
            self.db.query(OAuthClient)
            .filter(OAuthClient.client_id == client_id, OAuthClient.deleted_at.is_(None))
            .first()
        )

    def get_active_client(self, client_id: str) -> OAuthClient | None:
        """Get an active client by ID"""
        return (
            self.db.query(OAuthClient)
            .filter(
                OAuthClient.client_id == client_id,
                OAuthClient.is_active == True,
                OAuthClient.deleted_at.is_(None),
            )
            .first()
        )

    def client_id_exists(self, client_id: str) -> bool:
        """Check if a client_id exists (including soft-deleted clients).

        Used before creating a new client to prevent primary key violations.
        """
        return (
            self.db.query(OAuthClient).filter(OAuthClient.client_id == client_id).first()
            is not None
        )

    def create_client(self, client: OAuthClient) -> OAuthClient:
        """Create a new OAuth client"""
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def update_client(self, client: OAuthClient) -> OAuthClient:
        """Update an existing OAuth client"""
        client.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(client)
        return client

    def deactivate_client(self, client_id: str) -> bool:
        """Deactivate a client (soft disable)"""
        client = self.get_client(client_id)
        if client:
            client.is_active = False
            client.updated_at = datetime.now(UTC)
            self.db.commit()
            return True
        return False

    def delete_client(self, client_id: str) -> bool:
        """Soft delete a client"""
        client = self.get_client(client_id)
        if client:
            client.deleted_at = datetime.now(UTC)
            client.is_active = False
            self.db.commit()
            return True
        return False

    def purge_client(self, client_id: str) -> bool:
        """Hard delete a client; CASCADE removes related tokens and consents."""
        client = self.db.query(OAuthClient).filter(OAuthClient.client_id == client_id).first()

        if client:
            self.db.delete(client)
            self.db.commit()
            return True
        return False

    def list_all_clients(
        self, include_inactive: bool = False, offset: int = 0, limit: int = 20
    ) -> list[OAuthClient]:
        """List all OAuth clients with pagination."""
        query = self.db.query(OAuthClient).filter(OAuthClient.deleted_at.is_(None))

        if not include_inactive:
            query = query.filter(OAuthClient.is_active == True)

        return query.order_by(OAuthClient.created_at.desc()).offset(offset).limit(limit).all()

    def count_clients(self, include_inactive: bool = False) -> int:
        """Count total number of non-deleted clients."""
        query = self.db.query(OAuthClient).filter(OAuthClient.deleted_at.is_(None))

        if not include_inactive:
            query = query.filter(OAuthClient.is_active == True)

        return query.count()

    #
    # Authorization Code Operations
    #

    @staticmethod
    def generate_authorization_code() -> str:
        """Generate a cryptographically secure authorization code"""
        return secrets.token_urlsafe(64)

    def create_authorization_code(
        self,
        client_id: str,
        user_id: UUID,
        redirect_uri: str,
        scope: str,
        code_challenge: str,
        code_challenge_method: str = "S256",
        state: str | None = None,
        context_profile_id: UUID | None = None,
        nonce: str | None = None,
        expires_in_seconds: int = 600,  # 10 minutes
    ) -> OAuthAuthorizationCode:
        """Create a new authorization code"""
        code = self.generate_authorization_code()
        expires_at = datetime.now(UTC)
        from datetime import timedelta

        expires_at = expires_at + timedelta(seconds=expires_in_seconds)

        auth_code = OAuthAuthorizationCode(
            code=code,
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            context_profile_id=context_profile_id,
            nonce=nonce,
            expires_at=expires_at,
        )

        self.db.add(auth_code)
        self.db.commit()
        self.db.refresh(auth_code)
        return auth_code

    def get_authorization_code(self, code: str) -> OAuthAuthorizationCode | None:
        """Get an authorization code"""
        return (
            self.db.query(OAuthAuthorizationCode)
            .filter(OAuthAuthorizationCode.code == code)
            .first()
        )

    def get_valid_authorization_code(self, code: str) -> OAuthAuthorizationCode | None:
        """Get a valid (not expired, not used) authorization code"""
        auth_code = self.get_authorization_code(code)
        if auth_code and auth_code.is_valid:
            return auth_code
        return None

    def mark_authorization_code_used(self, code: str) -> bool:
        """Mark an authorization code as used"""
        auth_code = self.get_authorization_code(code)
        if auth_code:
            auth_code.used_at = datetime.now(UTC)
            self.db.commit()
            return True
        return False

    def delete_expired_authorization_codes(self) -> int:
        """Delete expired authorization codes (cleanup)"""
        now = datetime.now(UTC)
        result = (
            self.db.query(OAuthAuthorizationCode)
            .filter(
                or_(
                    OAuthAuthorizationCode.expires_at < now,
                    OAuthAuthorizationCode.used_at.isnot(None),
                )
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return result

    #
    # Access Token Operations
    #

    @staticmethod
    def generate_token() -> str:
        """Generate a cryptographically secure token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for storage using SHA-256"""
        return hashlib.sha256(token.encode()).hexdigest()

    def create_access_token(
        self,
        client_id: str,
        user_id: UUID,
        scope: str,
        context_profile_id: UUID | None = None,
        expires_in_seconds: int = 3600,  # 1 hour
    ) -> tuple[OAuthAccessToken, str]:
        """Create a new access token. Returns (model, raw token string)."""
        raw_token = self.generate_token()
        token_hash = self.hash_token(raw_token)

        from datetime import timedelta

        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_seconds)

        access_token = OAuthAccessToken(
            token_hash=token_hash,
            client_id=client_id,
            user_id=user_id,
            scope=scope,
            context_profile_id=context_profile_id,
            expires_at=expires_at,
        )

        self.db.add(access_token)
        self.db.commit()
        self.db.refresh(access_token)

        return access_token, raw_token

    def get_access_token_by_hash(self, token_hash: str) -> OAuthAccessToken | None:
        """Get an access token by its hash"""
        return (
            self.db.query(OAuthAccessToken)
            .filter(OAuthAccessToken.token_hash == token_hash)
            .first()
        )

    def get_access_token_by_raw(self, raw_token: str) -> OAuthAccessToken | None:
        """Get an access token by the raw token string"""
        token_hash = self.hash_token(raw_token)
        return self.get_access_token_by_hash(token_hash)

    def get_active_access_token(self, raw_token: str) -> OAuthAccessToken | None:
        """Get an active (not expired, not revoked) access token"""
        token = self.get_access_token_by_raw(raw_token)
        if token and token.is_active:
            return token
        return None

    def revoke_access_token(self, token_id: UUID) -> bool:
        """Revoke an access token"""
        token = self.db.query(OAuthAccessToken).filter(OAuthAccessToken.id == token_id).first()
        if token:
            token.revoked_at = datetime.now(UTC)
            self.db.commit()
            return True
        return False

    def revoke_access_token_by_raw(self, raw_token: str) -> bool:
        """Revoke an access token by its raw value"""
        token = self.get_access_token_by_raw(raw_token)
        if token:
            token.revoked_at = datetime.now(UTC)
            self.db.commit()
            return True
        return False

    def get_user_access_tokens(self, user_id: UUID) -> list[OAuthAccessToken]:
        """Get all access tokens for a user"""
        return (
            self.db.query(OAuthAccessToken)
            .filter(OAuthAccessToken.user_id == user_id)
            .order_by(OAuthAccessToken.issued_at.desc())
            .all()
        )

    def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """Revoke all access tokens for a user"""
        now = datetime.now(UTC)
        result = (
            self.db.query(OAuthAccessToken)
            .filter(OAuthAccessToken.user_id == user_id, OAuthAccessToken.revoked_at.is_(None))
            .update({OAuthAccessToken.revoked_at: now}, synchronize_session=False)
        )
        self.db.commit()
        return result

    #
    # Refresh Token Operations
    #

    def create_refresh_token(
        self,
        access_token_id: UUID,
        client_id: str,
        user_id: UUID,
        scope: str,
        expires_in_seconds: int = 2592000,  # 30 days
    ) -> tuple[OAuthRefreshToken, str]:
        """Create a new refresh token. Returns (model, raw token string)."""
        raw_token = self.generate_token()
        token_hash = self.hash_token(raw_token)

        from datetime import timedelta

        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_seconds)

        refresh_token = OAuthRefreshToken(
            token_hash=token_hash,
            access_token_id=access_token_id,
            client_id=client_id,
            user_id=user_id,
            scope=scope,
            expires_at=expires_at,
        )

        self.db.add(refresh_token)
        self.db.commit()
        self.db.refresh(refresh_token)

        return refresh_token, raw_token

    def get_refresh_token_by_hash(self, token_hash: str) -> OAuthRefreshToken | None:
        """Get a refresh token by its hash"""
        return (
            self.db.query(OAuthRefreshToken)
            .filter(OAuthRefreshToken.token_hash == token_hash)
            .first()
        )

    def get_refresh_token_by_raw(self, raw_token: str) -> OAuthRefreshToken | None:
        """Get a refresh token by the raw token string"""
        token_hash = self.hash_token(raw_token)
        return self.get_refresh_token_by_hash(token_hash)

    def get_active_refresh_token(self, raw_token: str) -> OAuthRefreshToken | None:
        """Get an active (not expired, not revoked, not rotated) refresh token"""
        token = self.get_refresh_token_by_raw(raw_token)
        if token and token.is_active:
            return token
        return None

    def rotate_refresh_token(
        self,
        old_token_id: UUID,
        new_access_token_id: UUID,
        client_id: str,
        user_id: UUID,
        scope: str,
        expires_in_seconds: int = 2592000,
    ) -> tuple[OAuthRefreshToken, str]:
        """Issue a new refresh token and mark the old one as rotated."""
        new_token, raw_token = self.create_refresh_token(
            access_token_id=new_access_token_id,
            client_id=client_id,
            user_id=user_id,
            scope=scope,
            expires_in_seconds=expires_in_seconds,
        )

        old_token = (
            self.db.query(OAuthRefreshToken).filter(OAuthRefreshToken.id == old_token_id).first()
        )
        if old_token:
            old_token.rotated_at = datetime.now(UTC)
            old_token.replaced_by_id = new_token.id
            self.db.commit()

        return new_token, raw_token

    def revoke_refresh_token(self, token_id: UUID) -> bool:
        """Revoke a refresh token"""
        token = self.db.query(OAuthRefreshToken).filter(OAuthRefreshToken.id == token_id).first()
        if token:
            token.revoked_at = datetime.now(UTC)
            self.db.commit()
            return True
        return False

    def revoke_refresh_token_by_raw(self, raw_token: str) -> bool:
        """Revoke a refresh token by its raw value"""
        token = self.get_refresh_token_by_raw(raw_token)
        if token:
            token.revoked_at = datetime.now(UTC)
            self.db.commit()
            return True
        return False

    def revoke_all_user_refresh_tokens(self, user_id: UUID) -> int:
        """Revoke all refresh tokens for a user"""
        now = datetime.now(UTC)
        result = (
            self.db.query(OAuthRefreshToken)
            .filter(
                OAuthRefreshToken.user_id == user_id,
                OAuthRefreshToken.revoked_at.is_(None),
                OAuthRefreshToken.rotated_at.is_(None),
            )
            .update({OAuthRefreshToken.revoked_at: now}, synchronize_session=False)
        )
        self.db.commit()
        return result

    #
    # Consent Operations
    #

    def get_consent(self, user_id: UUID, client_id: str) -> OAuthConsent | None:
        """Get the active consent for a user-client pair"""
        return (
            self.db.query(OAuthConsent)
            .filter(
                OAuthConsent.user_id == user_id,
                OAuthConsent.client_id == client_id,
                OAuthConsent.withdrawn_at.is_(None),
            )
            .first()
        )

    def get_consent_by_id(self, consent_id: UUID) -> OAuthConsent | None:
        """Get a consent by ID"""
        return self.db.query(OAuthConsent).filter(OAuthConsent.id == consent_id).first()

    def create_consent(
        self,
        user_id: UUID,
        client_id: str,
        granted_scopes: list[str],
        context_profile_id: UUID | None = None,
        consent_method: str = "explicit",
        ip_address: str | None = None,
        user_agent: str | None = None,
        expires_at: datetime | None = None,
    ) -> OAuthConsent:
        """Create or update a consent record for a user-client pair."""
        from src.models.oauth import ConsentMethod

        existing = self.get_consent(user_id, client_id)
        if existing:
            existing.granted_scopes = granted_scopes
            existing.context_profile_id = context_profile_id
            existing.granted_at = datetime.now(UTC)
            existing.expires_at = expires_at
            existing.ip_address = ip_address
            existing.user_agent = user_agent
            self.db.commit()
            self.db.refresh(existing)
            return existing

        consent = OAuthConsent(
            user_id=user_id,
            client_id=client_id,
            granted_scopes=granted_scopes,
            context_profile_id=context_profile_id,
            consent_method=ConsentMethod(consent_method),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )

        self.db.add(consent)
        self.db.commit()
        self.db.refresh(consent)
        return consent

    def withdraw_consent(self, user_id: UUID, client_id: str) -> bool:
        """Withdraw consent for a user-client pair"""
        consent = self.get_consent(user_id, client_id)
        if consent:
            consent.withdrawn_at = datetime.now(UTC)

            self.db.query(OAuthAccessToken).filter(
                OAuthAccessToken.user_id == user_id,
                OAuthAccessToken.client_id == client_id,
                OAuthAccessToken.revoked_at.is_(None),
            ).update({OAuthAccessToken.revoked_at: datetime.now(UTC)}, synchronize_session=False)

            self.db.query(OAuthRefreshToken).filter(
                OAuthRefreshToken.user_id == user_id,
                OAuthRefreshToken.client_id == client_id,
                OAuthRefreshToken.revoked_at.is_(None),
                OAuthRefreshToken.rotated_at.is_(None),
            ).update({OAuthRefreshToken.revoked_at: datetime.now(UTC)}, synchronize_session=False)

            self.db.commit()
            return True
        return False

    def get_user_consents(self, user_id: UUID) -> list[OAuthConsent]:
        """Get all consents (active and withdrawn) for a user"""
        return (
            self.db.query(OAuthConsent)
            .filter(OAuthConsent.user_id == user_id)
            .order_by(OAuthConsent.granted_at.desc())
            .all()
        )

    def get_user_active_consents(
        self, user_id: UUID, context_profile_id: UUID | None = None
    ) -> list[OAuthConsent]:
        """Get all active consents for a user, optionally filtered by context."""
        query = self.db.query(OAuthConsent).filter(
            OAuthConsent.user_id == user_id, OAuthConsent.withdrawn_at.is_(None)
        )
        if context_profile_id is not None:
            query = query.filter(OAuthConsent.context_profile_id == context_profile_id)
        return query.order_by(OAuthConsent.granted_at.desc()).all()

    def withdraw_all_user_consents(self, user_id: UUID) -> int:
        """Withdraw all active consents for a user. Used during account soft deletion."""
        now = datetime.now(UTC)
        count = (
            self.db.query(OAuthConsent)
            .filter(OAuthConsent.user_id == user_id, OAuthConsent.withdrawn_at.is_(None))
            .update({OAuthConsent.withdrawn_at: now}, synchronize_session=False)
        )
        self.db.commit()
        return count

    def has_valid_consent(self, user_id: UUID, client_id: str, required_scopes: list[str]) -> bool:
        """Check if user has valid consent covering all required scopes"""
        consent = self.get_consent(user_id, client_id)
        if not consent or not consent.is_active:
            return False
        return consent.has_all_scopes(required_scopes)
