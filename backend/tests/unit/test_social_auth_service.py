"""Tests for OAuth 2.0 social login business logic."""

from unittest.mock import Mock, patch

import pytest

from src.models.auth import AuthUser
from src.models.profile import AccountType
from src.services.social_auth_service import (
    AccountLinkingError,
    OAuthProviderNotConfiguredError,
    OAuthStateValidationError,
    OAuthTokenExchangeError,
    OAuthTokenVerificationError,
    SocialAuthService,
)


class TestPKCEGeneration:
    """Test PKCE code_verifier and code_challenge generation."""

    def test_generate_pkce_pair(self):
        """Test PKCE pair generation produces valid values."""
        service = SocialAuthService(Mock(), Mock())

        code_verifier, code_challenge = service.generate_pkce_pair()

        assert len(code_verifier) >= 43
        assert len(code_verifier) <= 128
        assert all(c.isalnum() or c in "-_" for c in code_verifier)

        # SHA-256 -> 32 bytes -> 43 chars base64url
        assert len(code_challenge) == 43
        assert all(c.isalnum() or c in "-_" for c in code_challenge)

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

    @patch("src.services.social_auth_service.settings")
    def test_generate_authorization_url_google(self, mock_settings):
        """Test Google authorization URL generation."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        mock_settings.GOOGLE_REDIRECT_URI = (
            "http://localhost:8000/api/v1/auth/social/google/callback"
        )

        service = SocialAuthService(Mock(), Mock())

        auth_url, state, code_verifier = service.generate_authorization_url("google")

        assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
        assert "client_id=test-client-id" in auth_url
        assert "redirect_uri=" in auth_url
        assert "code_challenge=" in auth_url
        assert "code_challenge_method=S256" in auth_url
        assert (
            "scope=openid+email+profile" in auth_url or "scope=openid%20email%20profile" in auth_url
        )
        assert "state=" in auth_url

        assert len(state) >= 32
        assert len(code_verifier) >= 43

    @patch("src.services.social_auth_service.settings")
    def test_generate_authorization_url_custom_state(self, mock_settings):
        """Test authorization URL generation with custom state."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        mock_settings.GOOGLE_REDIRECT_URI = "http://localhost:8000/callback"

        service = SocialAuthService(Mock(), Mock())
        custom_state = "custom-state-value"

        auth_url, state, code_verifier = service.generate_authorization_url(
            "google", state=custom_state
        )

        assert state == custom_state
        assert f"state={custom_state}" in auth_url

    @patch("src.services.social_auth_service.settings")
    def test_generate_authorization_url_not_configured(self, mock_settings):
        """Test error when OAuth credentials not configured."""
        mock_settings.GOOGLE_CLIENT_ID = None
        mock_settings.GOOGLE_CLIENT_SECRET = None

        service = SocialAuthService(Mock(), Mock())

        with pytest.raises(OAuthProviderNotConfiguredError) as exc_info:
            service.generate_authorization_url("google")

        assert "Google OAuth credentials not configured" in str(exc_info.value)

    @patch("src.services.social_auth_service.settings")
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

    @patch("src.services.social_auth_service.settings")
    @patch("src.services.social_auth_service.OAuth2Client")
    def test_exchange_code_for_token_success(self, mock_oauth_client_class, mock_settings):
        """Test successful token exchange."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        mock_settings.GOOGLE_REDIRECT_URI = "http://localhost:8000/callback"

        mock_client = Mock()
        mock_client.fetch_token.return_value = {
            "access_token": "mock-access-token",
            "id_token": "mock-id-token",
            "refresh_token": "mock-refresh-token",
            "expires_in": 3600,
        }
        mock_oauth_client_class.return_value = mock_client

        service = SocialAuthService(Mock(), Mock())

        token_response = service.exchange_code_for_token(
            provider="google",
            code="mock-auth-code",
            code_verifier="mock-verifier",
            state="state-123",
            expected_state="state-123",
        )

        assert token_response["access_token"] == "mock-access-token"
        assert token_response["id_token"] == "mock-id-token"
        assert "refresh_token" in token_response

    @patch("src.services.social_auth_service.settings")
    def test_exchange_code_state_mismatch(self, mock_settings):
        """Test state validation (CSRF protection)."""
        service = SocialAuthService(Mock(), Mock())

        with pytest.raises(OAuthStateValidationError) as exc_info:
            service.exchange_code_for_token(
                provider="google",
                code="mock-code",
                code_verifier="mock-verifier",
                state="wrong-state",
                expected_state="correct-state",
            )

        assert "State parameter mismatch" in str(exc_info.value)

    @patch("src.services.social_auth_service.settings")
    @patch("src.services.social_auth_service.OAuth2Client")
    def test_exchange_code_token_exchange_fails(self, mock_oauth_client_class, mock_settings):
        """Test error when token exchange fails."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        mock_settings.GOOGLE_REDIRECT_URI = "http://localhost:8000/callback"

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
                expected_state="state-123",
            )

        assert "Failed to exchange authorization code" in str(exc_info.value)


class TestIDTokenVerification:
    """Test Google ID token verification."""

    @patch("src.services.social_auth_service.settings")
    @patch("src.services.social_auth_service.httpx.get")
    @patch("src.services.social_auth_service.jwt.decode")
    def test_verify_google_id_token_success(self, mock_jwt_decode, mock_httpx_get, mock_settings):
        """Test successful ID token verification."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"

        mock_jwks_response = Mock()
        mock_jwks_response.json.return_value = {"keys": []}
        mock_jwks_response.raise_for_status = Mock()
        mock_httpx_get.return_value = mock_jwks_response

        mock_jwt_decode.return_value = {
            "sub": "google-user-123",
            "email": "user@gmail.com",
            "name": "Test User",
            "email_verified": True,
        }

        service = SocialAuthService(Mock(), Mock())

        claims = service.verify_google_id_token("mock-id-token")

        assert claims["sub"] == "google-user-123"
        assert claims["email"] == "user@gmail.com"
        assert claims["email_verified"] is True

    @patch("src.services.social_auth_service.settings")
    @patch("src.services.social_auth_service.httpx.get")
    @patch("src.services.social_auth_service.jwt.decode")
    def test_verify_google_id_token_missing_claims(
        self, mock_jwt_decode, mock_httpx_get, mock_settings
    ):
        """Test error when required claims missing."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"

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

    def test_existing_oauth_user_authentication(self):
        """Test authentication of existing OAuth user."""
        from uuid import uuid4

        from src.models.profile import BaseProfile

        mock_auth_repo = Mock()
        mock_profile_repo = Mock()
        user_uuid = str(uuid4())

        existing_user = AuthUser(
            id=str(uuid4()),
            user_id=user_uuid,
            email="user@gmail.com",
            password_hash="hashed",
            provider="google",
            provider_id="google-123",
            is_email_verified=True,
            is_admin=False,
            has_custom_password=False,
        )
        mock_auth_repo.get_by_provider = Mock(return_value=existing_user)
        mock_auth_repo.get_by_provider_including_deleted = Mock(return_value=None)
        mock_auth_repo.update_last_login = Mock()

        mock_profile = Mock(spec=BaseProfile)
        mock_profile.account_type = AccountType.verified
        mock_profile_repo.get_profile_by_id = Mock(return_value=mock_profile)

        service = SocialAuthService(mock_auth_repo, mock_profile_repo)

        (
            access_token,
            refresh_token,
            user_id,
            is_new_user,
            account_type,
            is_email_verified,
            is_admin,
            ret_provider,
            has_custom_password,
        ) = service.authenticate_or_create_user(
            provider="google",
            provider_id="google-123",
            email="user@gmail.com",
            display_name="Test User",
            email_verified=True,
        )

        assert access_token is not None
        assert refresh_token is not None
        assert user_id == user_uuid
        assert is_new_user is False
        assert account_type == "verified"
        assert is_email_verified is True
        assert is_admin is False
        assert ret_provider == "google"
        assert has_custom_password is False
        mock_auth_repo.update_last_login.assert_called_once()
        mock_profile_repo.get_profile_by_id.assert_called_once()

    def test_account_linking_required(self):
        """Test account linking error when email exists."""
        from uuid import uuid4

        mock_auth_repo = Mock()
        mock_profile_repo = Mock()

        mock_auth_repo.get_by_provider = Mock(return_value=None)
        mock_auth_repo.get_by_provider_including_deleted = Mock(return_value=None)

        existing_email_user = AuthUser(
            id=str(uuid4()),
            user_id=str(uuid4()),
            email="user@gmail.com",
            password_hash="hashed",
            provider=None,  # Email/password user
            provider_id=None,
        )
        mock_auth_repo.get_by_email = Mock(return_value=existing_email_user)

        service = SocialAuthService(mock_auth_repo, mock_profile_repo)

        with pytest.raises(AccountLinkingError) as exc_info:
            service.authenticate_or_create_user(
                provider="google",
                provider_id="google-new",
                email="user@gmail.com",
                display_name="Test User",
                email_verified=True,
            )

        assert "already registered with email/password" in str(exc_info.value)

    def test_create_new_oauth_user(self):
        """Test creating new user with OAuth credentials."""
        from uuid import uuid4

        from src.models.profile import BaseProfile

        mock_auth_repo = Mock()
        mock_profile_repo = Mock()

        mock_auth_repo.get_by_provider = Mock(return_value=None)
        mock_auth_repo.get_by_provider_including_deleted = Mock(return_value=None)
        mock_auth_repo.get_by_email = Mock(return_value=None)

        mock_profile = Mock(spec=BaseProfile)
        mock_profile.user_id = uuid4()
        mock_profile_repo.create_profile = Mock(return_value=mock_profile)
        mock_auth_repo.create_user = Mock()

        service = SocialAuthService(mock_auth_repo, mock_profile_repo)

        (
            access_token,
            refresh_token,
            user_id,
            is_new_user,
            account_type,
            is_email_verified,
            is_admin,
            ret_provider,
            has_custom_password,
        ) = service.authenticate_or_create_user(
            provider="google",
            provider_id="google-new",
            email="newuser@gmail.com",
            display_name="New User",
            email_verified=True,
        )

        assert access_token is not None
        assert refresh_token is not None
        assert user_id == str(mock_profile.user_id)
        assert is_new_user is True
        # OAuth registration always starts as unverified; identity
        # verification (account_type=verified) requires admin document review
        assert account_type == "unverified"
        assert is_email_verified is True
        assert is_admin is False
        assert ret_provider == "google"
        assert has_custom_password is False

        mock_profile_repo.create_profile.assert_called_once()
        mock_auth_repo.create_user.assert_called_once()

        call_args = mock_auth_repo.create_user.call_args
        assert call_args.kwargs["provider"] == "google"
        assert call_args.kwargs["provider_id"] == "google-new"
        assert call_args.kwargs["is_email_verified"] is True
