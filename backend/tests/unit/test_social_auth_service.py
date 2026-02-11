"""
Unit Tests for Social Authentication Service

Tests the business logic for OAuth 2.0 social login functionality.
Uses mocked repositories to isolate service layer logic.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import secrets

from src.services.social_auth_service import (
    SocialAuthService,
    OAuthProviderNotConfiguredError,
    OAuthStateValidationError,
    OAuthTokenExchangeError,
    OAuthTokenVerificationError,
    AccountLinkingError
)
from src.models.auth import AuthUser
from src.models.profile import AccountType


class TestPKCEGeneration:
    """Test PKCE code_verifier and code_challenge generation."""

    def test_generate_pkce_pair(self):
        """Test PKCE pair generation produces valid values."""
        service = SocialAuthService(Mock(), Mock())

        code_verifier, code_challenge = service.generate_pkce_pair()

        # Verify code_verifier is generated (43-128 chars for URL-safe base64)
        assert len(code_verifier) >= 43
        assert len(code_verifier) <= 128
        assert all(c.isalnum() or c in '-_' for c in code_verifier)

        # Verify code_challenge is generated (SHA-256 hash, base64 encoded)
        assert len(code_challenge) == 43  # SHA-256 -> 32 bytes -> 43 chars base64
        assert all(c.isalnum() or c in '-_' for c in code_challenge)

        # Verify they are different
        assert code_verifier != code_challenge

    def test_pkce_pair_uniqueness(self):
        """Test that each PKCE pair is unique."""
        service = SocialAuthService(Mock(), Mock())

        pair1 = service.generate_pkce_pair()
        pair2 = service.generate_pkce_pair()

        assert pair1[0] != pair2[0]  # Different verifiers
        assert pair1[1] != pair2[1]  # Different challenges


class TestAuthorizationURLGeneration:
    """Test OAuth authorization URL generation."""

    @patch('src.services.social_auth_service.settings')
    def test_generate_authorization_url_google(self, mock_settings):
        """Test Google authorization URL generation."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        mock_settings.GOOGLE_REDIRECT_URI = "http://localhost:8000/api/v1/auth/social/google/callback"

        service = SocialAuthService(Mock(), Mock())

        auth_url, state, code_verifier = service.generate_authorization_url("google")

        # Verify authorization URL contains required parameters
        assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
        assert "client_id=test-client-id" in auth_url
        assert "redirect_uri=" in auth_url
        assert "code_challenge=" in auth_url
        assert "code_challenge_method=S256" in auth_url
        assert "scope=openid+email+profile" in auth_url or "scope=openid%20email%20profile" in auth_url
        assert "state=" in auth_url

        # Verify state is generated
        assert len(state) >= 32

        # Verify code_verifier is generated
        assert len(code_verifier) >= 43

    @patch('src.services.social_auth_service.settings')
    def test_generate_authorization_url_custom_state(self, mock_settings):
        """Test authorization URL generation with custom state."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        mock_settings.GOOGLE_REDIRECT_URI = "http://localhost:8000/callback"

        service = SocialAuthService(Mock(), Mock())
        custom_state = "custom-state-value"

        auth_url, state, code_verifier = service.generate_authorization_url("google", state=custom_state)

        assert state == custom_state
        assert f"state={custom_state}" in auth_url

    @patch('src.services.social_auth_service.settings')
    def test_generate_authorization_url_not_configured(self, mock_settings):
        """Test error when OAuth credentials not configured."""
        mock_settings.GOOGLE_CLIENT_ID = None
        mock_settings.GOOGLE_CLIENT_SECRET = None

        service = SocialAuthService(Mock(), Mock())

        with pytest.raises(OAuthProviderNotConfiguredError) as exc_info:
            service.generate_authorization_url("google")

        assert "Google OAuth credentials not configured" in str(exc_info.value)

    @patch('src.services.social_auth_service.settings')
    def test_generate_authorization_url_invalid_provider(self, mock_settings):
        """Test error for unsupported provider."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"

        service = SocialAuthService(Mock(), Mock())

        with pytest.raises(ValueError) as exc_info:
            service.generate_authorization_url("invalid-provider")

        assert "Unsupported OAuth provider" in str(exc_info.value)


class TestTokenExchange:
    """Test authorization code exchange for tokens."""

    @patch('src.services.social_auth_service.settings')
    @patch('src.services.social_auth_service.OAuth2Client')
    def test_exchange_code_for_token_success(self, mock_oauth_client_class, mock_settings):
        """Test successful token exchange."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        mock_settings.GOOGLE_REDIRECT_URI = "http://localhost:8000/callback"

        # Mock OAuth client
        mock_client = Mock()
        mock_client.fetch_token.return_value = {
            "access_token": "mock-access-token",
            "id_token": "mock-id-token",
            "refresh_token": "mock-refresh-token",
            "expires_in": 3600
        }
        mock_oauth_client_class.return_value = mock_client

        service = SocialAuthService(Mock(), Mock())

        token_response = service.exchange_code_for_token(
            provider="google",
            code="mock-auth-code",
            code_verifier="mock-verifier",
            state="state-123",
            expected_state="state-123"
        )

        assert token_response["access_token"] == "mock-access-token"
        assert token_response["id_token"] == "mock-id-token"
        assert "refresh_token" in token_response

    @patch('src.services.social_auth_service.settings')
    def test_exchange_code_state_mismatch(self, mock_settings):
        """Test state validation (CSRF protection)."""
        service = SocialAuthService(Mock(), Mock())

        with pytest.raises(OAuthStateValidationError) as exc_info:
            service.exchange_code_for_token(
                provider="google",
                code="mock-code",
                code_verifier="mock-verifier",
                state="wrong-state",
                expected_state="correct-state"
            )

        assert "State parameter mismatch" in str(exc_info.value)

    @patch('src.services.social_auth_service.settings')
    @patch('src.services.social_auth_service.OAuth2Client')
    def test_exchange_code_token_exchange_fails(self, mock_oauth_client_class, mock_settings):
        """Test error when token exchange fails."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        mock_settings.GOOGLE_REDIRECT_URI = "http://localhost:8000/callback"

        # Mock OAuth client to raise exception
        mock_client = Mock()
        mock_client.fetch_token.side_effect = Exception("Network error")
        mock_oauth_client_class.return_value = mock_client

        service = SocialAuthService(Mock(), Mock())

        with pytest.raises(OAuthTokenExchangeError) as exc_info:
            service.exchange_code_for_token(
                provider="google",
                code="mock-code",
                code_verifier="mock-verifier",
                state="state-123",
                expected_state="state-123"
            )

        assert "Failed to exchange authorization code" in str(exc_info.value)


class TestIDTokenVerification:
    """Test Google ID token verification."""

    @patch('src.services.social_auth_service.settings')
    @patch('src.services.social_auth_service.httpx.get')
    @patch('src.services.social_auth_service.jwt.decode')
    def test_verify_google_id_token_success(self, mock_jwt_decode, mock_httpx_get, mock_settings):
        """Test successful ID token verification."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"

        # Mock JWKS fetch
        mock_jwks_response = Mock()
        mock_jwks_response.json.return_value = {"keys": []}
        mock_jwks_response.raise_for_status = Mock()
        mock_httpx_get.return_value = mock_jwks_response

        # Mock JWT decode
        mock_jwt_decode.return_value = {
            "sub": "google-user-123",
            "email": "user@gmail.com",
            "name": "Test User",
            "email_verified": True
        }

        service = SocialAuthService(Mock(), Mock())

        claims = service.verify_google_id_token("mock-id-token")

        assert claims["sub"] == "google-user-123"
        assert claims["email"] == "user@gmail.com"
        assert claims["email_verified"] is True

    @patch('src.services.social_auth_service.settings')
    @patch('src.services.social_auth_service.httpx.get')
    @patch('src.services.social_auth_service.jwt.decode')
    def test_verify_google_id_token_missing_claims(self, mock_jwt_decode, mock_httpx_get, mock_settings):
        """Test error when required claims missing."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"

        # Mock JWKS fetch
        mock_jwks_response = Mock()
        mock_jwks_response.json.return_value = {"keys": []}
        mock_jwks_response.raise_for_status = Mock()
        mock_httpx_get.return_value = mock_jwks_response

        # Mock JWT decode with missing claims
        mock_jwt_decode.return_value = {
            "sub": "google-user-123"
            # Missing 'email' claim
        }

        service = SocialAuthService(Mock(), Mock())

        with pytest.raises(OAuthTokenVerificationError) as exc_info:
            service.verify_google_id_token("mock-id-token")

        assert "Missing required claims" in str(exc_info.value)


class TestAuthenticateOrCreateUser:
    """Test user authentication or creation logic."""

    @pytest.mark.asyncio
    async def test_existing_oauth_user_authentication(self):
        """Test authentication of existing OAuth user."""
        from uuid import uuid4
        from src.models.profile import BaseProfile

        # Mock repositories
        mock_auth_repo = Mock()
        mock_profile_repo = Mock()

        # Generate valid UUID
        user_uuid = str(uuid4())

        # Existing OAuth user
        existing_user = AuthUser(
            id=str(uuid4()),
            user_id=user_uuid,
            email="user@gmail.com",
            password_hash="hashed",
            provider="google",
            provider_id="google-123"
        )
        mock_auth_repo.get_by_provider = AsyncMock(return_value=existing_user)
        mock_auth_repo.update_last_login = AsyncMock()

        # Mock profile for account_type
        mock_profile = Mock(spec=BaseProfile)
        mock_profile.account_type = AccountType.verified
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)

        service = SocialAuthService(mock_auth_repo, mock_profile_repo)

        access_token, refresh_token, is_new_user = await service.authenticate_or_create_user(
            provider="google",
            provider_id="google-123",
            email="user@gmail.com",
            display_name="Test User",
            email_verified=True
        )

        assert access_token is not None
        assert refresh_token is not None
        assert is_new_user is False
        mock_auth_repo.update_last_login.assert_called_once()
        mock_profile_repo.get_by_user_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_account_linking_required(self):
        """Test account linking error when email exists."""
        from uuid import uuid4

        # Mock repositories
        mock_auth_repo = Mock()
        mock_profile_repo = Mock()

        # No OAuth user, but email exists
        mock_auth_repo.get_by_provider = AsyncMock(return_value=None)

        existing_email_user = AuthUser(
            id=str(uuid4()),
            user_id=str(uuid4()),
            email="user@gmail.com",
            password_hash="hashed",
            provider=None,  # Email/password user
            provider_id=None
        )
        mock_auth_repo.get_by_email = AsyncMock(return_value=existing_email_user)

        service = SocialAuthService(mock_auth_repo, mock_profile_repo)

        with pytest.raises(AccountLinkingError) as exc_info:
            await service.authenticate_or_create_user(
                provider="google",
                provider_id="google-new",
                email="user@gmail.com",
                display_name="Test User",
                email_verified=True
            )

        assert "already registered with email/password" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_new_oauth_user(self):
        """Test creating new user with OAuth credentials."""
        # Mock repositories
        mock_auth_repo = Mock()
        mock_profile_repo = Mock()

        # No existing user
        mock_auth_repo.get_by_provider = AsyncMock(return_value=None)
        mock_auth_repo.get_by_email = AsyncMock(return_value=None)
        mock_profile_repo.create_base_profile = AsyncMock()
        mock_auth_repo.create_user = AsyncMock()

        service = SocialAuthService(mock_auth_repo, mock_profile_repo)

        access_token, refresh_token, is_new_user = await service.authenticate_or_create_user(
            provider="google",
            provider_id="google-new",
            email="newuser@gmail.com",
            display_name="New User",
            email_verified=True
        )

        assert access_token is not None
        assert refresh_token is not None
        assert is_new_user is True

        # Verify profile and auth user created
        mock_profile_repo.create_base_profile.assert_called_once()
        mock_auth_repo.create_user.assert_called_once()

        # Verify OAuth fields passed to create_user
        call_args = mock_auth_repo.create_user.call_args
        assert call_args.kwargs["provider"] == "google"
        assert call_args.kwargs["provider_id"] == "google-new"
        assert call_args.kwargs["is_email_verified"] is True
