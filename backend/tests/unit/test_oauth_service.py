"""Tests for PKCE validation, scope filtering, token issuance, and consent management."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.models.context import ContextType
from src.models.oauth import (
    OAuthAccessToken,
    OAuthAuthorizationCode,
    OAuthClient,
    OAuthConsent,
    OAuthRefreshToken,
    OAuthScope,
)
from src.models.profile import AccountType
from src.services.oauth_service import (
    IntrospectionResult,
    InvalidClientError,
    InvalidGrantError,
    InvalidRequestError,
    InvalidScopeError,
    OAuthService,
    TokenResponse,
)


class TestPKCEValidation:
    """Test PKCE (Proof Key for Code Exchange) validation."""

    def test_generate_pkce_challenge_creates_valid_hash(self):
        """Test PKCE challenge generation uses SHA-256 + base64url."""
        code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"

        challenge = OAuthService.generate_pkce_challenge(code_verifier)

        assert challenge is not None
        assert isinstance(challenge, str)
        # Base64url encoded SHA-256 is 43 characters (256 bits / 6 bits per char)
        assert len(challenge) == 43
        # Should not contain base64 padding
        assert "=" not in challenge

    def test_generate_pkce_challenge_known_value(self):
        """Test PKCE challenge matches known test vector."""
        # Test vector from RFC 7636 Appendix B
        code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        expected_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

        challenge = OAuthService.generate_pkce_challenge(code_verifier)

        assert challenge == expected_challenge

    def test_verify_pkce_with_correct_verifier(self):
        """Test PKCE verification succeeds with matching verifier."""
        code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        code_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

        result = OAuthService.verify_pkce(code_verifier, code_challenge)

        assert result is True

    def test_verify_pkce_with_incorrect_verifier(self):
        """Test PKCE verification fails with wrong verifier."""
        code_verifier = "wrong-verifier-value"
        code_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

        result = OAuthService.verify_pkce(code_verifier, code_challenge)

        assert result is False

    def test_verify_pkce_with_empty_verifier(self):
        """Test PKCE verification fails with empty verifier."""
        code_verifier = ""
        code_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

        result = OAuthService.verify_pkce(code_verifier, code_challenge)

        assert result is False


class TestClientValidation:
    """Test OAuth client validation."""

    @pytest.fixture
    def mock_oauth_repo(self):
        """Create mock OAuth repository."""
        return Mock()

    @pytest.fixture
    def oauth_service(self, mock_oauth_repo):
        """Create OAuthService with mocked repository."""
        return OAuthService(mock_oauth_repo)

    @pytest.fixture
    def sample_client(self):
        """Create a sample OAuth client."""
        client = Mock(spec=OAuthClient)
        client.client_id = "test-client"
        client.client_name = "Test Client"
        client.is_confidential = False
        client.is_active = True
        client.is_first_party = False
        client.redirect_uris = ["https://example.com/callback"]
        client.allowed_scopes = ["profile:read:basic", "email"]
        client.client_secret_hash = None
        client.is_redirect_uri_valid = Mock(return_value=True)
        client.can_request_scope = Mock(side_effect=lambda s: s in ["profile:read:basic", "email"])
        client.can_request_scopes = Mock(
            side_effect=lambda scopes: all(s in ["profile:read:basic", "email"] for s in scopes)
        )
        return client

    def test_get_client_returns_active_client(self, oauth_service, mock_oauth_repo, sample_client):
        """Test get_client returns active client."""
        mock_oauth_repo.get_active_client.return_value = sample_client

        result = oauth_service.get_client("test-client")

        assert result == sample_client
        mock_oauth_repo.get_active_client.assert_called_once_with("test-client")

    def test_get_client_raises_for_unknown_client(self, oauth_service, mock_oauth_repo):
        """Test get_client raises InvalidClientError for unknown client."""
        mock_oauth_repo.get_active_client.return_value = None

        with pytest.raises(InvalidClientError) as exc_info:
            oauth_service.get_client("unknown-client")

        assert "Unknown client" in str(exc_info.value.error_description)

    def test_validate_client_credentials_public_client_no_secret(
        self, oauth_service, mock_oauth_repo, sample_client
    ):
        """Test public client validation without secret."""
        sample_client.is_confidential = False
        mock_oauth_repo.get_active_client.return_value = sample_client

        result = oauth_service.validate_client_credentials("test-client")

        assert result == sample_client

    def test_validate_client_credentials_confidential_client_requires_secret(
        self, oauth_service, mock_oauth_repo, sample_client
    ):
        """Test confidential client requires secret."""
        sample_client.is_confidential = True
        mock_oauth_repo.get_active_client.return_value = sample_client

        with pytest.raises(InvalidClientError) as exc_info:
            oauth_service.validate_client_credentials("test-client")

        assert "secret required" in str(exc_info.value.error_description)

    @patch("passlib.hash.argon2.verify")
    def test_validate_client_credentials_confidential_client_valid_secret(
        self, mock_verify, oauth_service, mock_oauth_repo, sample_client
    ):
        """Test confidential client validation with valid secret."""
        sample_client.is_confidential = True
        sample_client.client_secret_hash = "$argon2id$..."
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_verify.return_value = True

        result = oauth_service.validate_client_credentials("test-client", "valid-secret")

        assert result == sample_client
        mock_verify.assert_called_once_with("valid-secret", "$argon2id$...")

    @patch("passlib.hash.argon2.verify")
    def test_validate_client_credentials_confidential_client_invalid_secret(
        self, mock_verify, oauth_service, mock_oauth_repo, sample_client
    ):
        """Test confidential client validation fails with invalid secret."""
        sample_client.is_confidential = True
        sample_client.client_secret_hash = "$argon2id$..."
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_verify.return_value = False

        with pytest.raises(InvalidClientError) as exc_info:
            oauth_service.validate_client_credentials("test-client", "wrong-secret")

        assert "Invalid client secret" in str(exc_info.value.error_description)

    def test_validate_redirect_uri_valid(self, oauth_service, sample_client):
        """Test redirect URI validation passes for registered URI."""
        sample_client.is_redirect_uri_valid.return_value = True

        # Should not raise
        oauth_service.validate_redirect_uri(sample_client, "https://example.com/callback")

        sample_client.is_redirect_uri_valid.assert_called_once_with("https://example.com/callback")

    def test_validate_redirect_uri_invalid(self, oauth_service, sample_client):
        """Test redirect URI validation fails for unregistered URI."""
        sample_client.is_redirect_uri_valid.return_value = False

        with pytest.raises(InvalidRequestError) as exc_info:
            oauth_service.validate_redirect_uri(sample_client, "https://evil.com/callback")

        assert "Invalid redirect_uri" in str(exc_info.value.error_description)


class TestScopeValidation:
    """Test OAuth scope validation and filtering."""

    @pytest.fixture
    def mock_oauth_repo(self):
        """Create mock OAuth repository."""
        repo = Mock()
        basic_scope = Mock(spec=OAuthScope)
        basic_scope.scope_name = "profile:read:basic"
        basic_scope.required_context_type = None
        basic_scope.is_sensitive = False

        email_scope = Mock(spec=OAuthScope)
        email_scope.scope_name = "email"
        email_scope.required_context_type = None
        email_scope.is_sensitive = True

        legal_scope = Mock(spec=OAuthScope)
        legal_scope.scope_name = "contexts:legal:read"
        legal_scope.required_context_type = ContextType.legal
        legal_scope.is_sensitive = True

        def get_scope(name):
            scopes = {
                "profile:read:basic": basic_scope,
                "email": email_scope,
                "contexts:legal:read": legal_scope,
            }
            return scopes.get(name)

        repo.get_scope = Mock(side_effect=get_scope)
        return repo

    @pytest.fixture
    def sample_client(self):
        """Create a sample OAuth client with allowed scopes."""
        client = Mock(spec=OAuthClient)
        client.client_id = "test-client"
        client.allowed_scopes = ["profile:read:basic", "email", "openid", "contexts:legal:read"]
        client.can_request_scope = Mock(
            side_effect=lambda s: (
                s in ["profile:read:basic", "email", "openid", "contexts:legal:read"]
            )
        )
        return client

    @pytest.fixture
    def oauth_service(self, mock_oauth_repo):
        """Create OAuthService with mocked repository."""
        return OAuthService(mock_oauth_repo)

    def test_validate_scopes_valid_scopes(self, oauth_service, sample_client):
        """Test scope validation passes for valid scopes."""
        result = oauth_service.validate_scopes(
            client=sample_client, requested_scopes=["profile:read:basic", "email"]
        )

        assert "profile:read:basic" in result
        assert "email" in result

    def test_validate_scopes_includes_openid(self, oauth_service, sample_client):
        """Test scope validation includes openid scope."""
        result = oauth_service.validate_scopes(
            client=sample_client, requested_scopes=["openid", "profile:read:basic"]
        )

        assert "openid" in result
        assert "profile:read:basic" in result

    def test_validate_scopes_client_not_allowed(self, oauth_service, sample_client):
        """Test scope validation fails for scopes client cannot request."""
        sample_client.can_request_scope = Mock(return_value=False)

        with pytest.raises(InvalidScopeError) as exc_info:
            oauth_service.validate_scopes(client=sample_client, requested_scopes=["admin:full"])

        assert "not authorized" in str(exc_info.value.error_description)

    def test_validate_scopes_unknown_scope(self, oauth_service, mock_oauth_repo, sample_client):
        """Test scope validation fails for unknown scope."""
        mock_oauth_repo.get_scope.return_value = None
        sample_client.can_request_scope = Mock(return_value=True)

        with pytest.raises(InvalidScopeError) as exc_info:
            oauth_service.validate_scopes(client=sample_client, requested_scopes=["unknown:scope"])

        assert "Unknown scope" in str(exc_info.value.error_description)

    def test_validate_scopes_context_restricted_without_context(self, oauth_service, sample_client):
        """Test context-restricted scope requires context type."""
        with pytest.raises(InvalidScopeError) as exc_info:
            oauth_service.validate_scopes(
                client=sample_client, requested_scopes=["contexts:legal:read"], context_type=None
            )

        assert "requires context type" in str(exc_info.value.error_description)

    def test_validate_scopes_context_restricted_wrong_context(self, oauth_service, sample_client):
        """Test context-restricted scope fails with wrong context."""
        with pytest.raises(InvalidScopeError) as exc_info:
            oauth_service.validate_scopes(
                client=sample_client,
                requested_scopes=["contexts:legal:read"],
                context_type=ContextType.social,  # Wrong context
            )

        assert "requires context type" in str(exc_info.value.error_description)

    def test_validate_scopes_context_restricted_correct_context(self, oauth_service, sample_client):
        """Test context-restricted scope passes with correct context."""
        result = oauth_service.validate_scopes(
            client=sample_client,
            requested_scopes=["contexts:legal:read"],
            context_type=ContextType.legal,
        )

        assert "contexts:legal:read" in result

    def test_validate_scopes_pseudonymous_account_blocked_from_legal(
        self, oauth_service, sample_client
    ):
        """Test pseudonymous accounts cannot access legal/healthcare scopes."""
        mock_profile = Mock()
        mock_profile.account_type = AccountType.pseudonymous

        with pytest.raises(InvalidScopeError) as exc_info:
            oauth_service.validate_scopes(
                client=sample_client,
                requested_scopes=["contexts:legal:read"],
                user_profile=mock_profile,
                context_type=ContextType.legal,
            )

        assert "Pseudonymous accounts cannot access" in str(exc_info.value.error_description)

    def test_validate_scopes_empty_scopes_raises(self, oauth_service, sample_client):
        """Test validation fails with empty scope list."""
        sample_client.can_request_scope = Mock(return_value=False)

        with pytest.raises(InvalidScopeError):
            oauth_service.validate_scopes(client=sample_client, requested_scopes=[])


class TestScopeBasedFiltering:
    """Test profile field filtering by OAuth scopes."""

    @pytest.fixture
    def oauth_service(self):
        """Create OAuthService without repository (not needed for filtering)."""
        return OAuthService(Mock())

    def test_filter_profile_fields_basic_scope(self, oauth_service):
        """Test filtering with profile:read:basic scope."""
        profile_data = {
            "sub": "user-123",
            "preferred_name": "Sarah",
            "display_name": "Dr. Sarah Chen",
            "avatar_url": "https://example.com/avatar.webp",
            "avatar_thumbnail_url": "https://example.com/thumb.webp",
            "primary_email": "sarah@example.com",
            "primary_phone": "+1-555-0101",
        }

        result = oauth_service.filter_profile_fields_by_scopes(
            profile_data=profile_data, scopes=["profile:read:basic"]
        )

        assert "preferred_name" in result
        assert "display_name" in result
        assert "avatar_url" in result
        assert "avatar_thumbnail_url" in result
        assert "primary_email" not in result
        assert "primary_phone" not in result

    def test_filter_profile_fields_email_scope(self, oauth_service):
        """Test filtering with email scope."""
        profile_data = {
            "sub": "user-123",
            "display_name": "Dr. Sarah Chen",
            "primary_email": "sarah@example.com",
            "email": "sarah@example.com",
            "email_verified": True,
        }

        result = oauth_service.filter_profile_fields_by_scopes(
            profile_data=profile_data, scopes=["email"]
        )

        assert "email" in result
        assert "primary_email" in result
        assert "email_verified" in result
        assert "display_name" not in result

    def test_filter_profile_fields_multiple_scopes(self, oauth_service):
        """Test filtering with multiple scopes."""
        profile_data = {
            "sub": "user-123",
            "preferred_name": "Sarah",
            "display_name": "Dr. Sarah Chen",
            "primary_email": "sarah@example.com",
            "email_verified": True,
            "primary_phone": "+1-555-0101",
        }

        result = oauth_service.filter_profile_fields_by_scopes(
            profile_data=profile_data, scopes=["profile:read:basic", "email"]
        )

        assert "preferred_name" in result
        assert "display_name" in result
        assert "primary_email" in result
        assert "email_verified" in result
        assert "primary_phone" not in result

    def test_filter_profile_fields_always_includes_sub(self, oauth_service):
        """Test sub claim is always included."""
        profile_data = {"sub": "user-123", "user_id": "user-123", "account_type": "verified"}

        result = oauth_service.filter_profile_fields_by_scopes(
            profile_data=profile_data,
            scopes=[],  # No scopes
        )

        assert "sub" in result
        assert "user_id" in result
        assert "account_type" in result


class TestAuthorizationCodeFlow:
    """Test OAuth 2.1 Authorization Code Flow."""

    @pytest.fixture
    def mock_oauth_repo(self):
        """Create mock OAuth repository."""
        return Mock()

    @pytest.fixture
    def oauth_service(self, mock_oauth_repo):
        """Create OAuthService with mocked repository."""
        return OAuthService(mock_oauth_repo)

    @pytest.fixture
    def sample_client(self):
        """Create a sample OAuth client."""
        client = Mock(spec=OAuthClient)
        client.client_id = "test-client"
        client.client_name = "Test Client"
        client.is_confidential = False
        client.is_active = True
        client.redirect_uris = ["https://example.com/callback"]
        client.allowed_scopes = ["profile:read:basic", "email", "offline_access"]
        client.is_redirect_uri_valid = Mock(return_value=True)
        return client

    def test_create_authorization_code_success(self, oauth_service, mock_oauth_repo, sample_client):
        """Test successful authorization code creation."""
        user_id = uuid4()
        mock_oauth_repo.get_active_client.return_value = sample_client

        mock_auth_code = Mock(spec=OAuthAuthorizationCode)
        mock_auth_code.code = "test-auth-code"
        mock_oauth_repo.create_authorization_code.return_value = mock_auth_code

        result = oauth_service.create_authorization_code(
            client_id="test-client",
            user_id=user_id,
            redirect_uri="https://example.com/callback",
            scope="profile:read:basic email",
            code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            code_challenge_method="S256",
        )

        assert result == mock_auth_code
        mock_oauth_repo.create_authorization_code.assert_called_once()

    def test_create_authorization_code_rejects_plain_pkce(
        self, oauth_service, mock_oauth_repo, sample_client
    ):
        """Test authorization code creation rejects plain PKCE method."""
        user_id = uuid4()
        mock_oauth_repo.get_active_client.return_value = sample_client

        with pytest.raises(InvalidRequestError) as exc_info:
            oauth_service.create_authorization_code(
                client_id="test-client",
                user_id=user_id,
                redirect_uri="https://example.com/callback",
                scope="profile:read:basic",
                code_challenge="plain-challenge",
                code_challenge_method="plain",  # Not allowed in OAuth 2.1
            )

        assert "S256" in str(exc_info.value.error_description)


class TestTokenExchange:
    """Test authorization code exchange for tokens."""

    @pytest.fixture
    def mock_oauth_repo(self):
        """Create mock OAuth repository."""
        return Mock()

    @pytest.fixture
    def oauth_service(self, mock_oauth_repo):
        """Create OAuthService with mocked repository."""
        return OAuthService(mock_oauth_repo)

    @pytest.fixture
    def sample_client(self):
        """Create a sample OAuth client."""
        client = Mock(spec=OAuthClient)
        client.client_id = "test-client"
        client.is_confidential = False
        client.client_secret_hash = None
        return client

    @pytest.fixture
    def sample_auth_code(self):
        """Create a sample authorization code."""
        auth_code = Mock(spec=OAuthAuthorizationCode)
        auth_code.code = "test-auth-code"
        auth_code.client_id = "test-client"
        auth_code.user_id = uuid4()
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.scope = "profile:read:basic email offline_access"
        auth_code.code_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
        auth_code.code_challenge_method = "S256"
        auth_code.context_profile_id = None
        auth_code.is_valid = True
        auth_code.is_expired = False
        auth_code.is_used = False
        return auth_code

    def test_exchange_authorization_code_success(
        self, oauth_service, mock_oauth_repo, sample_client, sample_auth_code
    ):
        """Test successful authorization code exchange."""
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_oauth_repo.get_valid_authorization_code.return_value = sample_auth_code

        access_token_model = Mock(spec=OAuthAccessToken)
        access_token_model.id = uuid4()
        mock_oauth_repo.create_access_token.return_value = (
            access_token_model,
            "access-token-value",
        )

        refresh_token_model = Mock(spec=OAuthRefreshToken)
        mock_oauth_repo.create_refresh_token.return_value = (
            refresh_token_model,
            "refresh-token-value",
        )

        result = oauth_service.exchange_authorization_code(
            code="test-auth-code",
            client_id="test-client",
            redirect_uri="https://example.com/callback",
            code_verifier="dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
        )

        assert isinstance(result, TokenResponse)
        assert result.access_token == "access-token-value"
        assert result.refresh_token == "refresh-token-value"
        assert result.token_type == "Bearer"
        assert result.expires_in == 3600

        mock_oauth_repo.mark_authorization_code_used.assert_called_once_with("test-auth-code")

    def test_exchange_authorization_code_invalid_code(
        self, oauth_service, mock_oauth_repo, sample_client
    ):
        """Test exchange fails with invalid code."""
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_oauth_repo.get_valid_authorization_code.return_value = None

        with pytest.raises(InvalidGrantError) as exc_info:
            oauth_service.exchange_authorization_code(
                code="invalid-code",
                client_id="test-client",
                redirect_uri="https://example.com/callback",
                code_verifier="verifier",
            )

        assert "invalid or expired" in str(exc_info.value.error_description)

    def test_exchange_authorization_code_wrong_client(
        self, oauth_service, mock_oauth_repo, sample_client, sample_auth_code
    ):
        """Test exchange fails when client_id doesn't match."""
        sample_auth_code.client_id = "different-client"
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_oauth_repo.get_valid_authorization_code.return_value = sample_auth_code

        with pytest.raises(InvalidGrantError) as exc_info:
            oauth_service.exchange_authorization_code(
                code="test-auth-code",
                client_id="test-client",
                redirect_uri="https://example.com/callback",
                code_verifier="verifier",
            )

        assert "another client" in str(exc_info.value.error_description)

    def test_exchange_authorization_code_wrong_redirect_uri(
        self, oauth_service, mock_oauth_repo, sample_client, sample_auth_code
    ):
        """Test exchange fails when redirect_uri doesn't match."""
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_oauth_repo.get_valid_authorization_code.return_value = sample_auth_code

        with pytest.raises(InvalidGrantError) as exc_info:
            oauth_service.exchange_authorization_code(
                code="test-auth-code",
                client_id="test-client",
                redirect_uri="https://evil.com/callback",  # Wrong URI
                code_verifier="dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
            )

        assert "redirect_uri mismatch" in str(exc_info.value.error_description)

    def test_exchange_authorization_code_pkce_verification_fails(
        self, oauth_service, mock_oauth_repo, sample_client, sample_auth_code
    ):
        """Test exchange fails when PKCE verification fails."""
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_oauth_repo.get_valid_authorization_code.return_value = sample_auth_code

        with pytest.raises(InvalidGrantError) as exc_info:
            oauth_service.exchange_authorization_code(
                code="test-auth-code",
                client_id="test-client",
                redirect_uri="https://example.com/callback",
                code_verifier="wrong-verifier",  # PKCE will fail
            )

        assert "PKCE verification failed" in str(exc_info.value.error_description)


class TestRefreshTokenRotation:
    """Test refresh token rotation (OAuth 2.1 requirement)."""

    @pytest.fixture
    def mock_oauth_repo(self):
        """Create mock OAuth repository."""
        return Mock()

    @pytest.fixture
    def oauth_service(self, mock_oauth_repo):
        """Create OAuthService with mocked repository."""
        return OAuthService(mock_oauth_repo)

    @pytest.fixture
    def sample_client(self):
        """Create a sample OAuth client."""
        client = Mock(spec=OAuthClient)
        client.client_id = "test-client"
        client.is_confidential = False
        return client

    @pytest.fixture
    def sample_refresh_token(self):
        """Create a sample refresh token."""
        token = Mock(spec=OAuthRefreshToken)
        token.id = uuid4()
        token.client_id = "test-client"
        token.user_id = uuid4()
        token.scope = "profile:read:basic offline_access"
        token.is_active = True
        token.is_expired = False
        token.is_revoked = False
        token.is_rotated = False
        return token

    def test_refresh_access_token_success_with_rotation(
        self, oauth_service, mock_oauth_repo, sample_client, sample_refresh_token
    ):
        """Test successful refresh token rotation."""
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_oauth_repo.get_active_refresh_token.return_value = sample_refresh_token

        new_access_token = Mock(spec=OAuthAccessToken)
        new_access_token.id = uuid4()
        mock_oauth_repo.create_access_token.return_value = (new_access_token, "new-access-token")

        new_refresh_token = Mock(spec=OAuthRefreshToken)
        mock_oauth_repo.rotate_refresh_token.return_value = (new_refresh_token, "new-refresh-token")

        result = oauth_service.refresh_access_token(
            refresh_token="old-refresh-token", client_id="test-client"
        )

        assert isinstance(result, TokenResponse)
        assert result.access_token == "new-access-token"
        assert result.refresh_token == "new-refresh-token"

        mock_oauth_repo.rotate_refresh_token.assert_called_once()

    def test_refresh_access_token_invalid_token(
        self, oauth_service, mock_oauth_repo, sample_client
    ):
        """Test refresh fails with invalid token."""
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_oauth_repo.get_active_refresh_token.return_value = None

        with pytest.raises(InvalidGrantError) as exc_info:
            oauth_service.refresh_access_token(
                refresh_token="invalid-token", client_id="test-client"
            )

        assert "invalid or expired" in str(exc_info.value.error_description)

    def test_refresh_access_token_wrong_client(
        self, oauth_service, mock_oauth_repo, sample_client, sample_refresh_token
    ):
        """Test refresh fails when client doesn't match."""
        sample_refresh_token.client_id = "different-client"
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_oauth_repo.get_active_refresh_token.return_value = sample_refresh_token

        with pytest.raises(InvalidGrantError) as exc_info:
            oauth_service.refresh_access_token(
                refresh_token="refresh-token", client_id="test-client"
            )

        assert "another client" in str(exc_info.value.error_description)

    def test_refresh_access_token_scope_reduction(
        self, oauth_service, mock_oauth_repo, sample_client, sample_refresh_token
    ):
        """Test refresh with reduced scope."""
        sample_refresh_token.scope = "profile:read:basic email offline_access"
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_oauth_repo.get_active_refresh_token.return_value = sample_refresh_token

        new_access_token = Mock(spec=OAuthAccessToken)
        new_access_token.id = uuid4()
        mock_oauth_repo.create_access_token.return_value = (new_access_token, "new-access-token")

        new_refresh_token = Mock(spec=OAuthRefreshToken)
        mock_oauth_repo.rotate_refresh_token.return_value = (new_refresh_token, "new-refresh-token")

        result = oauth_service.refresh_access_token(
            refresh_token="refresh-token",
            client_id="test-client",
            scope="profile:read:basic offline_access",  # Reduced scope
        )

        assert result.scope == "profile:read:basic offline_access"

    def test_refresh_access_token_scope_expansion_rejected(
        self, oauth_service, mock_oauth_repo, sample_client, sample_refresh_token
    ):
        """Test refresh rejects scope expansion."""
        sample_refresh_token.scope = "profile:read:basic offline_access"
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_oauth_repo.get_active_refresh_token.return_value = sample_refresh_token

        with pytest.raises(InvalidScopeError) as exc_info:
            oauth_service.refresh_access_token(
                refresh_token="refresh-token",
                client_id="test-client",
                scope="profile:read:basic email offline_access",  # Trying to add email
            )

        assert "subset" in str(exc_info.value.error_description)


class TestTokenIntrospection:
    """Test token introspection (RFC 7662)."""

    @pytest.fixture
    def mock_oauth_repo(self):
        """Create mock OAuth repository."""
        return Mock()

    @pytest.fixture
    def oauth_service(self, mock_oauth_repo):
        """Create OAuthService with mocked repository."""
        return OAuthService(mock_oauth_repo)

    def test_introspect_active_access_token(self, oauth_service, mock_oauth_repo):
        """Test introspection of active access token."""
        user_id = uuid4()
        access_token = Mock(spec=OAuthAccessToken)
        access_token.is_active = True
        access_token.scope = "profile:read:basic email"
        access_token.client_id = "test-client"
        access_token.user_id = user_id
        access_token.context_profile_id = None
        access_token.expires_at = datetime.now(UTC) + timedelta(hours=1)
        access_token.issued_at = datetime.now(UTC)

        mock_oauth_repo.get_access_token_by_raw.return_value = access_token

        result = oauth_service.introspect_token("valid-token")

        assert isinstance(result, IntrospectionResult)
        assert result.active is True
        assert result.scope == "profile:read:basic email"
        assert result.client_id == "test-client"
        assert result.token_type == "access_token"

    def test_introspect_expired_access_token(self, oauth_service, mock_oauth_repo):
        """Test introspection of expired access token."""
        access_token = Mock(spec=OAuthAccessToken)
        access_token.is_active = False

        mock_oauth_repo.get_access_token_by_raw.return_value = access_token

        result = oauth_service.introspect_token("expired-token")

        assert result.active is False

    def test_introspect_unknown_token(self, oauth_service, mock_oauth_repo):
        """Test introspection of unknown token."""
        mock_oauth_repo.get_access_token_by_raw.return_value = None
        mock_oauth_repo.get_refresh_token_by_raw.return_value = None

        result = oauth_service.introspect_token("unknown-token")

        assert result.active is False

    def test_introspect_active_refresh_token(self, oauth_service, mock_oauth_repo):
        """Test introspection of active refresh token."""
        user_id = uuid4()
        mock_oauth_repo.get_access_token_by_raw.return_value = None

        refresh_token = Mock(spec=OAuthRefreshToken)
        refresh_token.is_active = True
        refresh_token.scope = "profile:read:basic offline_access"
        refresh_token.client_id = "test-client"
        refresh_token.user_id = user_id
        refresh_token.expires_at = datetime.now(UTC) + timedelta(days=30)
        refresh_token.issued_at = datetime.now(UTC)

        mock_oauth_repo.get_refresh_token_by_raw.return_value = refresh_token

        result = oauth_service.introspect_token("refresh-token")

        assert result.active is True
        assert result.token_type == "refresh_token"


class TestTokenRevocation:
    """Test token revocation (RFC 7009)."""

    @pytest.fixture
    def mock_oauth_repo(self):
        """Create mock OAuth repository."""
        return Mock()

    @pytest.fixture
    def oauth_service(self, mock_oauth_repo):
        """Create OAuthService with mocked repository."""
        return OAuthService(mock_oauth_repo)

    def test_revoke_access_token(self, oauth_service, mock_oauth_repo):
        """Test access token revocation."""
        mock_oauth_repo.revoke_access_token_by_raw.return_value = True

        result = oauth_service.revoke_token("valid-access-token")

        assert result is True
        mock_oauth_repo.revoke_access_token_by_raw.assert_called_once_with("valid-access-token")

    def test_revoke_refresh_token(self, oauth_service, mock_oauth_repo):
        """Test refresh token revocation."""
        mock_oauth_repo.revoke_access_token_by_raw.return_value = False
        mock_oauth_repo.revoke_refresh_token_by_raw.return_value = True

        result = oauth_service.revoke_token("valid-refresh-token")

        assert result is True

    def test_revoke_unknown_token_succeeds(self, oauth_service, mock_oauth_repo):
        """Test revocation of unknown token returns success (RFC 7009)."""
        mock_oauth_repo.revoke_access_token_by_raw.return_value = False
        mock_oauth_repo.revoke_refresh_token_by_raw.return_value = False

        # Per RFC 7009, should still return success
        result = oauth_service.revoke_token("unknown-token")

        assert result is True


class TestConsentManagement:
    """Test OAuth consent management."""

    @pytest.fixture
    def mock_oauth_repo(self):
        """Create mock OAuth repository."""
        return Mock()

    @pytest.fixture
    def oauth_service(self, mock_oauth_repo):
        """Create OAuthService with mocked repository."""
        return OAuthService(mock_oauth_repo)

    @pytest.fixture
    def sample_client(self):
        """Create a sample OAuth client."""
        client = Mock(spec=OAuthClient)
        client.client_id = "test-client"
        client.allowed_scopes = ["profile:read:basic", "email"]
        client.can_request_scope = Mock(return_value=True)
        return client

    def test_record_consent_success(self, oauth_service, mock_oauth_repo, sample_client):
        """Test successful consent recording."""
        user_id = uuid4()
        mock_oauth_repo.get_active_client.return_value = sample_client

        basic_scope = Mock(spec=OAuthScope)
        basic_scope.required_context_type = None
        basic_scope.is_sensitive = False
        mock_oauth_repo.get_scope.return_value = basic_scope

        consent = Mock(spec=OAuthConsent)
        mock_oauth_repo.create_consent.return_value = consent

        result = oauth_service.record_consent(
            user_id=user_id,
            client_id="test-client",
            granted_scopes=["profile:read:basic"],
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert result == consent
        mock_oauth_repo.create_consent.assert_called_once()

    def test_check_consent_exists(self, oauth_service, mock_oauth_repo):
        """Test checking existing consent."""
        user_id = uuid4()
        mock_oauth_repo.has_valid_consent.return_value = True

        result = oauth_service.check_consent(
            user_id=user_id, client_id="test-client", required_scopes=["profile:read:basic"]
        )

        assert result is True

    def test_check_consent_not_exists(self, oauth_service, mock_oauth_repo):
        """Test checking non-existent consent."""
        user_id = uuid4()
        mock_oauth_repo.has_valid_consent.return_value = False

        result = oauth_service.check_consent(
            user_id=user_id, client_id="test-client", required_scopes=["profile:read:basic"]
        )

        assert result is False

    def test_withdraw_consent(self, oauth_service, mock_oauth_repo):
        """Test consent withdrawal."""
        user_id = uuid4()
        mock_oauth_repo.withdraw_consent.return_value = True

        result = oauth_service.withdraw_consent(user_id, "test-client")

        assert result is True
        mock_oauth_repo.withdraw_consent.assert_called_once_with(user_id, "test-client")

    def test_get_user_consents(self, oauth_service, mock_oauth_repo):
        """Test getting user's active consents."""
        user_id = uuid4()
        consents = [Mock(spec=OAuthConsent), Mock(spec=OAuthConsent)]
        mock_oauth_repo.get_user_active_consents.return_value = consents

        result = oauth_service.get_user_consents(user_id)

        assert len(result) == 2
        mock_oauth_repo.get_user_active_consents.assert_called_once_with(user_id, None)

    def test_get_user_consents_with_context_filter(self, oauth_service, mock_oauth_repo):
        """Test that context_profile_id is forwarded to the repository."""
        user_id = uuid4()
        context_id = uuid4()
        mock_oauth_repo.get_user_active_consents.return_value = []

        oauth_service.get_user_consents(user_id, context_profile_id=context_id)

        mock_oauth_repo.get_user_active_consents.assert_called_once_with(user_id, context_id)


class TestContextVerificationGuard:
    """Test that OAuth authorization code creation rejects unverified
    legal/healthcare contexts while allowing other context types."""

    @pytest.fixture
    def mock_oauth_repo(self):
        """Create mock OAuth repository."""
        return Mock()

    @pytest.fixture
    def mock_context_repo(self):
        """Create mock context repository."""
        return Mock()

    @pytest.fixture
    def oauth_service(self, mock_oauth_repo, mock_context_repo):
        """Create OAuthService with mocked repos including context_repo."""
        return OAuthService(mock_oauth_repo, context_repo=mock_context_repo)

    @pytest.fixture
    def sample_client(self):
        """Create a sample OAuth client for auth code tests."""
        client = Mock(spec=OAuthClient)
        client.client_id = "test-client"
        client.is_confidential = False
        client.is_active = True
        client.redirect_uris = ["https://example.com/callback"]
        client.is_redirect_uri_valid = Mock(return_value=True)
        return client

    def _make_context(self, context_type, verification_status, requires_verification, is_verified):
        """Helper to build a mock ContextProfile with verification fields."""
        ctx = Mock()
        ctx.context_type = context_type
        ctx.verification_status = verification_status
        ctx.requires_verification = requires_verification
        ctx.is_identity_verified = is_verified
        return ctx

    def test_allows_professional_context_without_verification(
        self, oauth_service, mock_oauth_repo, mock_context_repo, sample_client
    ):
        """Professional contexts do not require verification and should
        pass through regardless of verification_status."""
        user_id = uuid4()
        context_id = uuid4()
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_context_repo.get_context_profile_by_id.return_value = self._make_context(
            ContextType.professional, None, False, False
        )
        mock_auth_code = Mock(spec=OAuthAuthorizationCode)
        mock_auth_code.code = "auth-code"
        mock_oauth_repo.create_authorization_code.return_value = mock_auth_code

        result = oauth_service.create_authorization_code(
            client_id="test-client",
            user_id=user_id,
            redirect_uri="https://example.com/callback",
            scope="profile:read:basic",
            code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            code_challenge_method="S256",
            context_profile_id=context_id,
        )

        assert result == mock_auth_code

    def test_allows_legal_context_when_verified(
        self, oauth_service, mock_oauth_repo, mock_context_repo, sample_client
    ):
        """Legal context with verification_status=verified should be accepted."""
        user_id = uuid4()
        context_id = uuid4()
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_context_repo.get_context_profile_by_id.return_value = self._make_context(
            ContextType.legal, "verified", True, True
        )
        mock_auth_code = Mock(spec=OAuthAuthorizationCode)
        mock_auth_code.code = "auth-code"
        mock_oauth_repo.create_authorization_code.return_value = mock_auth_code

        result = oauth_service.create_authorization_code(
            client_id="test-client",
            user_id=user_id,
            redirect_uri="https://example.com/callback",
            scope="profile:read:basic",
            code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            code_challenge_method="S256",
            context_profile_id=context_id,
        )

        assert result == mock_auth_code

    def test_rejects_legal_context_when_pending(
        self, oauth_service, mock_oauth_repo, mock_context_repo, sample_client
    ):
        """Legal context with verification_status=pending must be rejected."""
        user_id = uuid4()
        context_id = uuid4()
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_context_repo.get_context_profile_by_id.return_value = self._make_context(
            ContextType.legal, "pending", True, False
        )

        with pytest.raises(InvalidRequestError) as exc_info:
            oauth_service.create_authorization_code(
                client_id="test-client",
                user_id=user_id,
                redirect_uri="https://example.com/callback",
                scope="profile:read:basic",
                code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                code_challenge_method="S256",
                context_profile_id=context_id,
            )

        assert "verification" in exc_info.value.error_description.lower()

    def test_rejects_legal_context_when_rejected(
        self, oauth_service, mock_oauth_repo, mock_context_repo, sample_client
    ):
        """Legal context with verification_status=rejected must be rejected."""
        user_id = uuid4()
        context_id = uuid4()
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_context_repo.get_context_profile_by_id.return_value = self._make_context(
            ContextType.legal, "rejected", True, False
        )

        with pytest.raises(InvalidRequestError):
            oauth_service.create_authorization_code(
                client_id="test-client",
                user_id=user_id,
                redirect_uri="https://example.com/callback",
                scope="profile:read:basic",
                code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                code_challenge_method="S256",
                context_profile_id=context_id,
            )

    def test_rejects_healthcare_context_when_under_review(
        self, oauth_service, mock_oauth_repo, mock_context_repo, sample_client
    ):
        """Healthcare context with verification_status=under_review must be rejected."""
        user_id = uuid4()
        context_id = uuid4()
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_context_repo.get_context_profile_by_id.return_value = self._make_context(
            ContextType.healthcare, "under_review", True, False
        )

        with pytest.raises(InvalidRequestError):
            oauth_service.create_authorization_code(
                client_id="test-client",
                user_id=user_id,
                redirect_uri="https://example.com/callback",
                scope="profile:read:basic",
                code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                code_challenge_method="S256",
                context_profile_id=context_id,
            )

    def test_no_context_passes_through(
        self, oauth_service, mock_oauth_repo, mock_context_repo, sample_client
    ):
        """When context_profile_id is None, no verification check occurs."""
        user_id = uuid4()
        mock_oauth_repo.get_active_client.return_value = sample_client
        mock_auth_code = Mock(spec=OAuthAuthorizationCode)
        mock_auth_code.code = "auth-code"
        mock_oauth_repo.create_authorization_code.return_value = mock_auth_code

        result = oauth_service.create_authorization_code(
            client_id="test-client",
            user_id=user_id,
            redirect_uri="https://example.com/callback",
            scope="profile:read:basic",
            code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            code_challenge_method="S256",
            context_profile_id=None,
        )

        assert result == mock_auth_code
        mock_context_repo.get_context_profile_by_id.assert_not_called()

    def test_introspect_includes_context_verified_true_for_verified_legal(
        self, mock_oauth_repo, mock_context_repo
    ):
        """Token introspection reports context_verified=True when the bound
        legal context has been verified."""
        service = OAuthService(mock_oauth_repo, context_repo=mock_context_repo)
        user_id = uuid4()
        context_id = uuid4()

        access_token = Mock(spec=OAuthAccessToken)
        access_token.is_active = True
        access_token.scope = "profile:read:basic"
        access_token.client_id = "test-client"
        access_token.user_id = user_id
        access_token.context_profile_id = context_id
        access_token.expires_at = datetime.now(UTC) + timedelta(hours=1)
        access_token.issued_at = datetime.now(UTC)
        mock_oauth_repo.get_access_token_by_raw.return_value = access_token

        mock_context_repo.get_context_profile_by_id.return_value = self._make_context(
            ContextType.legal, "verified", True, True
        )

        result = service.introspect_token("some-token")

        assert result.active is True
        assert result.context_verified is True

    def test_introspect_includes_context_verified_false_for_pending_legal(
        self, mock_oauth_repo, mock_context_repo
    ):
        """Token introspection reports context_verified=False when the bound
        legal context is still pending."""
        service = OAuthService(mock_oauth_repo, context_repo=mock_context_repo)
        user_id = uuid4()
        context_id = uuid4()

        access_token = Mock(spec=OAuthAccessToken)
        access_token.is_active = True
        access_token.scope = "profile:read:basic"
        access_token.client_id = "test-client"
        access_token.user_id = user_id
        access_token.context_profile_id = context_id
        access_token.expires_at = datetime.now(UTC) + timedelta(hours=1)
        access_token.issued_at = datetime.now(UTC)
        mock_oauth_repo.get_access_token_by_raw.return_value = access_token

        mock_context_repo.get_context_profile_by_id.return_value = self._make_context(
            ContextType.legal, "pending", True, False
        )

        result = service.introspect_token("some-token")

        assert result.active is True
        assert result.context_verified is False

    def test_introspect_context_verified_none_for_professional(
        self, mock_oauth_repo, mock_context_repo
    ):
        """Token introspection reports context_verified=None when the bound
        context type does not require verification."""
        service = OAuthService(mock_oauth_repo, context_repo=mock_context_repo)
        user_id = uuid4()
        context_id = uuid4()

        access_token = Mock(spec=OAuthAccessToken)
        access_token.is_active = True
        access_token.scope = "profile:read:basic"
        access_token.client_id = "test-client"
        access_token.user_id = user_id
        access_token.context_profile_id = context_id
        access_token.expires_at = datetime.now(UTC) + timedelta(hours=1)
        access_token.issued_at = datetime.now(UTC)
        mock_oauth_repo.get_access_token_by_raw.return_value = access_token

        mock_context_repo.get_context_profile_by_id.return_value = self._make_context(
            ContextType.professional, None, False, False
        )

        result = service.introspect_token("some-token")

        assert result.active is True
        assert result.context_verified is None
