"""
Unit Tests for OAuth Repository

Tests data access layer for OAuth 2.1 entities.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from src.repositories.oauth_repository import OAuthRepository
from src.models.oauth import (
    OAuthScope,
    OAuthClient,
    OAuthAuthorizationCode,
    OAuthAccessToken,
    OAuthRefreshToken,
    OAuthConsent,
    TokenEndpointAuthMethod,
    ConsentMethod,
    AccessLevel
)
from src.models.profile import BaseProfile, AccountType
from src.models.context import ContextProfile, ContextType


class TestOAuthScopeOperations:
    """Test OAuth scope repository operations."""

    @pytest.fixture
    def oauth_repo(self, db_session: Session) -> OAuthRepository:
        """Create OAuthRepository with test session."""
        return OAuthRepository(db_session)

    @pytest.fixture
    def sample_scope(self, db_session: Session) -> OAuthScope:
        """Create a sample OAuth scope."""
        scope = OAuthScope(
            scope_name="test:scope",
            description="Test scope for unit tests",
            access_level=AccessLevel.read,
            allowed_fields=["field1", "field2"],
            is_sensitive=False
        )
        db_session.add(scope)
        db_session.commit()
        db_session.refresh(scope)
        return scope

    def test_get_scope_returns_scope(self, oauth_repo, sample_scope):
        """Test getting scope by name."""
        result = oauth_repo.get_scope("test:scope")

        assert result is not None
        assert result.scope_name == "test:scope"
        assert result.description == "Test scope for unit tests"

    def test_get_scope_returns_none_for_unknown(self, oauth_repo):
        """Test getting unknown scope returns None."""
        result = oauth_repo.get_scope("unknown:scope")

        assert result is None

    def test_get_scopes_returns_multiple(self, oauth_repo, db_session: Session):
        """Test getting multiple scopes by name."""
        # Create multiple scopes
        scope1 = OAuthScope(scope_name="scope:one", description="First scope")
        scope2 = OAuthScope(scope_name="scope:two", description="Second scope")
        db_session.add_all([scope1, scope2])
        db_session.commit()

        result = oauth_repo.get_scopes(["scope:one", "scope:two"])

        assert len(result) == 2
        scope_names = [s.scope_name for s in result]
        assert "scope:one" in scope_names
        assert "scope:two" in scope_names

    def test_list_all_scopes(self, oauth_repo, db_session: Session):
        """Test listing all scopes."""
        # Create scopes
        scope1 = OAuthScope(scope_name="list:one", description="First")
        scope2 = OAuthScope(scope_name="list:two", description="Second")
        db_session.add_all([scope1, scope2])
        db_session.commit()

        result = oauth_repo.list_all_scopes()

        assert len(result) >= 2


class TestOAuthClientOperations:
    """Test OAuth client repository operations."""

    @pytest.fixture
    def oauth_repo(self, db_session: Session) -> OAuthRepository:
        """Create OAuthRepository with test session."""
        return OAuthRepository(db_session)

    @pytest.fixture
    def sample_client(self, db_session: Session) -> OAuthClient:
        """Create a sample OAuth client."""
        client = OAuthClient(
            client_id="test-client-123",
            client_name="Test Client",
            client_description="A test OAuth client",
            redirect_uris=["https://example.com/callback"],
            allowed_scopes=["profile:read:basic", "email"],
            is_confidential=False,
            is_active=True,
            is_first_party=False,
            token_endpoint_auth_method=TokenEndpointAuthMethod.none
        )
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        return client

    def test_get_client_returns_client(self, oauth_repo, sample_client):
        """Test getting client by ID."""
        result = oauth_repo.get_client("test-client-123")

        assert result is not None
        assert result.client_id == "test-client-123"
        assert result.client_name == "Test Client"

    def test_get_client_returns_none_for_deleted(self, oauth_repo, db_session, sample_client):
        """Test deleted client is not returned."""
        sample_client.deleted_at = datetime.now(timezone.utc)
        db_session.commit()

        result = oauth_repo.get_client("test-client-123")

        assert result is None

    def test_get_active_client_returns_active(self, oauth_repo, sample_client):
        """Test getting active client."""
        result = oauth_repo.get_active_client("test-client-123")

        assert result is not None
        assert result.is_active is True

    def test_get_active_client_returns_none_for_inactive(self, oauth_repo, db_session, sample_client):
        """Test inactive client is not returned."""
        sample_client.is_active = False
        db_session.commit()

        result = oauth_repo.get_active_client("test-client-123")

        assert result is None

    def test_deactivate_client(self, oauth_repo, sample_client):
        """Test deactivating client."""
        result = oauth_repo.deactivate_client("test-client-123")

        assert result is True
        # Verify client is deactivated
        client = oauth_repo.get_client("test-client-123")
        assert client.is_active is False

    def test_delete_client_soft_deletes(self, oauth_repo, sample_client):
        """Test soft deleting client."""
        result = oauth_repo.delete_client("test-client-123")

        assert result is True
        # Client should not be returned
        client = oauth_repo.get_client("test-client-123")
        assert client is None


class TestAuthorizationCodeOperations:
    """Test authorization code repository operations."""

    @pytest.fixture
    def oauth_repo(self, db_session: Session) -> OAuthRepository:
        """Create OAuthRepository with test session."""
        return OAuthRepository(db_session)

    @pytest.fixture
    def sample_profile(self, db_session: Session) -> BaseProfile:
        """Create a sample user profile."""
        profile = BaseProfile(
            account_type=AccountType.verified,
            primary_email="test@example.com",
            preferred_language="en"
        )
        db_session.add(profile)
        db_session.commit()
        db_session.refresh(profile)
        return profile

    @pytest.fixture
    def sample_client(self, db_session: Session) -> OAuthClient:
        """Create a sample OAuth client."""
        client = OAuthClient(
            client_id="auth-code-client",
            client_name="Auth Code Client",
            redirect_uris=["https://example.com/callback"],
            allowed_scopes=["profile:read:basic"],
            is_active=True
        )
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        return client

    def test_generate_authorization_code_is_random(self, oauth_repo):
        """Test authorization code generation produces random values."""
        code1 = oauth_repo.generate_authorization_code()
        code2 = oauth_repo.generate_authorization_code()

        assert code1 != code2
        assert len(code1) > 40  # URL-safe base64

    def test_create_authorization_code(self, oauth_repo, sample_profile, sample_client):
        """Test creating authorization code."""
        auth_code = oauth_repo.create_authorization_code(
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            redirect_uri="https://example.com/callback",
            scope="profile:read:basic",
            code_challenge="test-challenge",
            code_challenge_method="S256",
            state="test-state"
        )

        assert auth_code is not None
        assert auth_code.code is not None
        assert auth_code.client_id == sample_client.client_id
        assert auth_code.user_id == sample_profile.user_id
        assert auth_code.scope == "profile:read:basic"
        assert auth_code.code_challenge == "test-challenge"
        # Check expiry is in the future (SQLite returns naive datetimes)
        expires_at = auth_code.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        assert expires_at > datetime.now(timezone.utc)

    def test_get_valid_authorization_code(self, oauth_repo, sample_profile, sample_client):
        """Test getting valid authorization code."""
        auth_code = oauth_repo.create_authorization_code(
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            redirect_uri="https://example.com/callback",
            scope="profile:read:basic",
            code_challenge="test-challenge"
        )

        result = oauth_repo.get_valid_authorization_code(auth_code.code)

        assert result is not None
        assert result.code == auth_code.code

    def test_get_valid_authorization_code_returns_none_for_used(
        self, oauth_repo, db_session, sample_profile, sample_client
    ):
        """Test used authorization code is not returned as valid."""
        auth_code = oauth_repo.create_authorization_code(
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            redirect_uri="https://example.com/callback",
            scope="profile:read:basic",
            code_challenge="test-challenge"
        )
        # Mark as used
        auth_code.used_at = datetime.now(timezone.utc)
        db_session.commit()

        result = oauth_repo.get_valid_authorization_code(auth_code.code)

        assert result is None

    def test_mark_authorization_code_used(self, oauth_repo, sample_profile, sample_client):
        """Test marking authorization code as used."""
        auth_code = oauth_repo.create_authorization_code(
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            redirect_uri="https://example.com/callback",
            scope="profile:read:basic",
            code_challenge="test-challenge"
        )

        result = oauth_repo.mark_authorization_code_used(auth_code.code)

        assert result is True
        # Verify code is marked used
        code = oauth_repo.get_authorization_code(auth_code.code)
        assert code.used_at is not None


class TestAccessTokenOperations:
    """Test access token repository operations."""

    @pytest.fixture
    def oauth_repo(self, db_session: Session) -> OAuthRepository:
        """Create OAuthRepository with test session."""
        return OAuthRepository(db_session)

    @pytest.fixture
    def sample_profile(self, db_session: Session) -> BaseProfile:
        """Create a sample user profile."""
        profile = BaseProfile(
            account_type=AccountType.verified,
            primary_email="token-test@example.com",
            preferred_language="en"
        )
        db_session.add(profile)
        db_session.commit()
        db_session.refresh(profile)
        return profile

    @pytest.fixture
    def sample_client(self, db_session: Session) -> OAuthClient:
        """Create a sample OAuth client."""
        client = OAuthClient(
            client_id="token-client",
            client_name="Token Client",
            redirect_uris=["https://example.com/callback"],
            allowed_scopes=["profile:read:basic"],
            is_active=True
        )
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        return client

    def test_generate_token_is_random(self, oauth_repo):
        """Test token generation produces random values."""
        token1 = oauth_repo.generate_token()
        token2 = oauth_repo.generate_token()

        assert token1 != token2
        assert len(token1) > 30

    def test_hash_token_produces_sha256(self, oauth_repo):
        """Test token hashing produces SHA-256 hash."""
        token = "test-token-value"
        hash1 = oauth_repo.hash_token(token)
        hash2 = oauth_repo.hash_token(token)

        # Same token produces same hash
        assert hash1 == hash2
        # SHA-256 is 64 hex characters
        assert len(hash1) == 64

    def test_create_access_token(self, oauth_repo, sample_profile, sample_client):
        """Test creating access token."""
        token_model, raw_token = oauth_repo.create_access_token(
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            scope="profile:read:basic"
        )

        assert token_model is not None
        assert raw_token is not None
        assert token_model.token_hash == oauth_repo.hash_token(raw_token)
        assert token_model.client_id == sample_client.client_id
        assert token_model.user_id == sample_profile.user_id
        # Check expiry is in the future (SQLite returns naive datetimes)
        expires_at = token_model.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        assert expires_at > datetime.now(timezone.utc)

    def test_get_active_access_token(self, oauth_repo, sample_profile, sample_client):
        """Test getting active access token by raw value."""
        token_model, raw_token = oauth_repo.create_access_token(
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            scope="profile:read:basic"
        )

        result = oauth_repo.get_active_access_token(raw_token)

        assert result is not None
        assert result.id == token_model.id

    def test_get_active_access_token_returns_none_for_revoked(
        self, oauth_repo, db_session, sample_profile, sample_client
    ):
        """Test revoked token is not returned as active."""
        token_model, raw_token = oauth_repo.create_access_token(
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            scope="profile:read:basic"
        )
        token_model.revoked_at = datetime.now(timezone.utc)
        db_session.commit()

        result = oauth_repo.get_active_access_token(raw_token)

        assert result is None

    def test_revoke_access_token(self, oauth_repo, sample_profile, sample_client):
        """Test revoking access token."""
        token_model, raw_token = oauth_repo.create_access_token(
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            scope="profile:read:basic"
        )

        result = oauth_repo.revoke_access_token(token_model.id)

        assert result is True
        # Verify token is revoked
        token = oauth_repo.get_access_token_by_hash(token_model.token_hash)
        assert token.revoked_at is not None

    def test_revoke_access_token_by_raw(self, oauth_repo, sample_profile, sample_client):
        """Test revoking access token by raw value."""
        token_model, raw_token = oauth_repo.create_access_token(
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            scope="profile:read:basic"
        )

        result = oauth_repo.revoke_access_token_by_raw(raw_token)

        assert result is True


class TestRefreshTokenOperations:
    """Test refresh token repository operations."""

    @pytest.fixture
    def oauth_repo(self, db_session: Session) -> OAuthRepository:
        """Create OAuthRepository with test session."""
        return OAuthRepository(db_session)

    @pytest.fixture
    def sample_profile(self, db_session: Session) -> BaseProfile:
        """Create a sample user profile."""
        profile = BaseProfile(
            account_type=AccountType.verified,
            primary_email="refresh-test@example.com",
            preferred_language="en"
        )
        db_session.add(profile)
        db_session.commit()
        db_session.refresh(profile)
        return profile

    @pytest.fixture
    def sample_client(self, db_session: Session) -> OAuthClient:
        """Create a sample OAuth client."""
        client = OAuthClient(
            client_id="refresh-client",
            client_name="Refresh Client",
            redirect_uris=["https://example.com/callback"],
            allowed_scopes=["profile:read:basic", "offline_access"],
            is_active=True
        )
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        return client

    @pytest.fixture
    def sample_access_token(
        self, oauth_repo, sample_profile, sample_client
    ) -> tuple[OAuthAccessToken, str]:
        """Create a sample access token."""
        return oauth_repo.create_access_token(
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            scope="profile:read:basic offline_access"
        )

    def test_create_refresh_token(
        self, oauth_repo, sample_profile, sample_client, sample_access_token
    ):
        """Test creating refresh token."""
        access_token, _ = sample_access_token

        refresh_model, raw_refresh = oauth_repo.create_refresh_token(
            access_token_id=access_token.id,
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            scope="profile:read:basic offline_access"
        )

        assert refresh_model is not None
        assert raw_refresh is not None
        assert refresh_model.token_hash == oauth_repo.hash_token(raw_refresh)
        assert refresh_model.access_token_id == access_token.id
        # Check expiry is in the future (SQLite returns naive datetimes)
        expires_at = refresh_model.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        assert expires_at > datetime.now(timezone.utc)

    def test_get_active_refresh_token(
        self, oauth_repo, sample_profile, sample_client, sample_access_token
    ):
        """Test getting active refresh token."""
        access_token, _ = sample_access_token

        refresh_model, raw_refresh = oauth_repo.create_refresh_token(
            access_token_id=access_token.id,
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            scope="profile:read:basic"
        )

        result = oauth_repo.get_active_refresh_token(raw_refresh)

        assert result is not None
        assert result.id == refresh_model.id

    def test_rotate_refresh_token(
        self, oauth_repo, db_session, sample_profile, sample_client, sample_access_token
    ):
        """Test refresh token rotation."""
        access_token, _ = sample_access_token

        # Create original refresh token
        old_refresh, old_raw = oauth_repo.create_refresh_token(
            access_token_id=access_token.id,
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            scope="profile:read:basic offline_access"
        )

        # Create new access token for rotation
        new_access, _ = oauth_repo.create_access_token(
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            scope="profile:read:basic offline_access"
        )

        # Rotate
        new_refresh, new_raw = oauth_repo.rotate_refresh_token(
            old_token_id=old_refresh.id,
            new_access_token_id=new_access.id,
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            scope="profile:read:basic offline_access"
        )

        assert new_refresh is not None
        assert new_raw != old_raw

        # Verify old token is marked as rotated
        db_session.refresh(old_refresh)
        assert old_refresh.rotated_at is not None
        assert old_refresh.replaced_by_id == new_refresh.id

        # Verify old token is no longer active
        result = oauth_repo.get_active_refresh_token(old_raw)
        assert result is None


class TestConsentOperations:
    """Test consent repository operations."""

    @pytest.fixture
    def oauth_repo(self, db_session: Session) -> OAuthRepository:
        """Create OAuthRepository with test session."""
        return OAuthRepository(db_session)

    @pytest.fixture
    def sample_profile(self, db_session: Session) -> BaseProfile:
        """Create a sample user profile."""
        profile = BaseProfile(
            account_type=AccountType.verified,
            primary_email="consent-test@example.com",
            preferred_language="en"
        )
        db_session.add(profile)
        db_session.commit()
        db_session.refresh(profile)
        return profile

    @pytest.fixture
    def sample_client(self, db_session: Session) -> OAuthClient:
        """Create a sample OAuth client."""
        client = OAuthClient(
            client_id="consent-client",
            client_name="Consent Client",
            redirect_uris=["https://example.com/callback"],
            allowed_scopes=["profile:read:basic", "email"],
            is_active=True
        )
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        return client

    def test_create_consent(self, oauth_repo, sample_profile, sample_client):
        """Test creating consent record."""
        consent = oauth_repo.create_consent(
            user_id=sample_profile.user_id,
            client_id=sample_client.client_id,
            granted_scopes=["profile:read:basic", "email"],
            consent_method="explicit",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )

        assert consent is not None
        assert consent.user_id == sample_profile.user_id
        assert consent.client_id == sample_client.client_id
        assert "profile:read:basic" in consent.granted_scopes
        assert "email" in consent.granted_scopes
        assert consent.ip_address == "192.168.1.1"

    def test_get_consent(self, oauth_repo, sample_profile, sample_client):
        """Test getting consent by user-client pair."""
        oauth_repo.create_consent(
            user_id=sample_profile.user_id,
            client_id=sample_client.client_id,
            granted_scopes=["profile:read:basic"]
        )

        result = oauth_repo.get_consent(sample_profile.user_id, sample_client.client_id)

        assert result is not None
        assert result.client_id == sample_client.client_id

    def test_get_consent_returns_none_for_withdrawn(
        self, oauth_repo, db_session, sample_profile, sample_client
    ):
        """Test withdrawn consent is not returned."""
        consent = oauth_repo.create_consent(
            user_id=sample_profile.user_id,
            client_id=sample_client.client_id,
            granted_scopes=["profile:read:basic"]
        )
        consent.withdrawn_at = datetime.now(timezone.utc)
        db_session.commit()

        result = oauth_repo.get_consent(sample_profile.user_id, sample_client.client_id)

        assert result is None

    def test_withdraw_consent(self, oauth_repo, sample_profile, sample_client):
        """Test withdrawing consent."""
        oauth_repo.create_consent(
            user_id=sample_profile.user_id,
            client_id=sample_client.client_id,
            granted_scopes=["profile:read:basic"]
        )

        result = oauth_repo.withdraw_consent(sample_profile.user_id, sample_client.client_id)

        assert result is True
        # Verify consent is withdrawn
        consent = oauth_repo.get_consent(sample_profile.user_id, sample_client.client_id)
        assert consent is None

    def test_withdraw_consent_revokes_tokens(
        self, oauth_repo, sample_profile, sample_client
    ):
        """Test withdrawing consent revokes associated tokens."""
        # Create consent
        oauth_repo.create_consent(
            user_id=sample_profile.user_id,
            client_id=sample_client.client_id,
            granted_scopes=["profile:read:basic", "offline_access"]
        )

        # Create tokens
        access_token, raw_access = oauth_repo.create_access_token(
            client_id=sample_client.client_id,
            user_id=sample_profile.user_id,
            scope="profile:read:basic"
        )

        # Withdraw consent
        oauth_repo.withdraw_consent(sample_profile.user_id, sample_client.client_id)

        # Verify token is revoked
        result = oauth_repo.get_active_access_token(raw_access)
        assert result is None

    def test_has_valid_consent_true(self, oauth_repo, sample_profile, sample_client):
        """Test checking valid consent returns true."""
        oauth_repo.create_consent(
            user_id=sample_profile.user_id,
            client_id=sample_client.client_id,
            granted_scopes=["profile:read:basic", "email"]
        )

        result = oauth_repo.has_valid_consent(
            user_id=sample_profile.user_id,
            client_id=sample_client.client_id,
            required_scopes=["profile:read:basic"]
        )

        assert result is True

    def test_has_valid_consent_false_missing_scope(
        self, oauth_repo, sample_profile, sample_client
    ):
        """Test checking consent with missing scope returns false."""
        oauth_repo.create_consent(
            user_id=sample_profile.user_id,
            client_id=sample_client.client_id,
            granted_scopes=["profile:read:basic"]
        )

        result = oauth_repo.has_valid_consent(
            user_id=sample_profile.user_id,
            client_id=sample_client.client_id,
            required_scopes=["profile:read:basic", "email"]  # email not granted
        )

        assert result is False

    def test_get_user_active_consents(self, oauth_repo, db_session, sample_profile):
        """Test getting user's active consents."""
        # Create multiple clients and consents
        client1 = OAuthClient(
            client_id="consent-client-1",
            client_name="Client 1",
            redirect_uris=["https://example1.com/callback"],
            is_active=True
        )
        client2 = OAuthClient(
            client_id="consent-client-2",
            client_name="Client 2",
            redirect_uris=["https://example2.com/callback"],
            is_active=True
        )
        db_session.add_all([client1, client2])
        db_session.commit()

        oauth_repo.create_consent(
            user_id=sample_profile.user_id,
            client_id=client1.client_id,
            granted_scopes=["profile:read:basic"]
        )
        oauth_repo.create_consent(
            user_id=sample_profile.user_id,
            client_id=client2.client_id,
            granted_scopes=["email"]
        )

        result = oauth_repo.get_user_active_consents(sample_profile.user_id)

        assert len(result) == 2

    def test_create_consent_updates_existing(
        self, oauth_repo, sample_profile, sample_client
    ):
        """Test creating consent updates existing consent instead of creating duplicate."""
        # Create initial consent
        consent1 = oauth_repo.create_consent(
            user_id=sample_profile.user_id,
            client_id=sample_client.client_id,
            granted_scopes=["profile:read:basic"]
        )

        # Create new consent with different scopes
        consent2 = oauth_repo.create_consent(
            user_id=sample_profile.user_id,
            client_id=sample_client.client_id,
            granted_scopes=["profile:read:basic", "email"]
        )

        # Should be the same consent record, updated
        assert consent1.id == consent2.id
        assert "email" in consent2.granted_scopes
