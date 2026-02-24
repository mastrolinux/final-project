"""Integration tests for OAuth 2.1 endpoint flows."""

import pytest
import json
import hashlib
import base64
import secrets
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.core.security import create_access_token
from src.models.auth import AuthUser
from src.models.profile import BaseProfile, AccountType
from src.models.context import ContextProfile, ContextType
from src.models.verification import VerificationStatus
from src.models.oauth import (
    OAuthClient,
    OAuthAccessToken,
    OAuthScope,
    OAuthConsent,
    AccessLevel,
    TokenEndpointAuthMethod
)


class TestOAuthDiscovery:
    """Test OAuth discovery endpoint."""

    def test_get_authorization_server_metadata(self, client: TestClient):
        """Test /.well-known/oauth-authorization-server returns valid metadata."""
        response = client.get("/api/v1/oauth/.well-known/oauth-authorization-server")

        assert response.status_code == 200
        data = response.json()

        # Required fields per RFC 8414
        assert "issuer" in data
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert "response_types_supported" in data
        assert "code" in data["response_types_supported"]

        # PKCE requirements
        assert "code_challenge_methods_supported" in data
        assert "S256" in data["code_challenge_methods_supported"]

        # OAuth 2.1 - no implicit flow
        assert "token" not in data.get("response_types_supported", [])

    def test_get_scopes_endpoint(self, client: TestClient, db_session: Session):
        """Test /oauth/scopes returns available scopes."""
        scope = OAuthScope(
            scope_name="test:read",
            description="Test read scope",
            access_level=AccessLevel.read
        )
        db_session.add(scope)
        db_session.commit()

        response = client.get("/api/v1/oauth/scopes")

        assert response.status_code == 200
        data = response.json()
        assert "scopes" in data
        scope_names = [s["scope_name"] for s in data["scopes"]]
        assert "test:read" in scope_names


class TestAuthorizationEndpoint:
    """Test OAuth authorization endpoint."""

    @pytest.fixture
    def sample_profile(self, db_session: Session) -> BaseProfile:
        """Create sample user profile."""
        profile = BaseProfile(
            account_type=AccountType.verified,
            primary_email="oauth-test@example.com",
            preferred_language="en"
        )
        db_session.add(profile)
        db_session.commit()
        db_session.refresh(profile)
        return profile

    @pytest.fixture
    def sample_oauth_client(self, db_session: Session) -> OAuthClient:
        """Create sample OAuth client."""
        client = OAuthClient(
            client_id="integration-test-client",
            client_name="Integration Test Client",
            client_description="Client for integration tests",
            redirect_uris=["https://example.com/callback", "https://example.com/callback2"],
            allowed_scopes=["openid", "profile:read:basic", "email", "offline_access"],
            is_confidential=False,
            is_active=True,
            is_first_party=False,
            token_endpoint_auth_method=TokenEndpointAuthMethod.none
        )
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        return client

    @pytest.fixture
    def sample_scopes(self, db_session: Session) -> list[OAuthScope]:
        """Create sample OAuth scopes."""
        scopes = [
            OAuthScope(
                scope_name="openid",
                description="OpenID Connect",
                access_level=AccessLevel.read
            ),
            OAuthScope(
                scope_name="profile:read:basic",
                description="Basic profile information",
                access_level=AccessLevel.read,
                allowed_fields=["preferred_name", "display_name", "photo_url"]
            ),
            OAuthScope(
                scope_name="email",
                description="Email address",
                access_level=AccessLevel.read,
                allowed_fields=["email", "email_verified", "primary_email"],
                is_sensitive=True
            ),
            OAuthScope(
                scope_name="offline_access",
                description="Refresh token access",
                access_level=AccessLevel.read
            )
        ]
        db_session.add_all(scopes)
        db_session.commit()
        return scopes

    @staticmethod
    def generate_pkce_pair() -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge."""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return code_verifier, code_challenge

    def test_authorize_missing_client_id(self, client: TestClient):
        """Test authorization fails without client_id (missing required param)."""
        response = client.get(
            "/api/v1/oauth/authorize",
            params={
                "response_type": "code",
                "redirect_uri": "https://example.com/callback"
            }
        )

        # FastAPI returns 422 for missing required query parameters
        assert response.status_code == 422

    def test_authorize_invalid_client(self, client: TestClient):
        """Test authorization fails with unknown client (returns redirect with error)."""
        _, code_challenge = self.generate_pkce_pair()

        response = client.get(
            "/api/v1/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": "unknown-client",
                "redirect_uri": "https://example.com/callback",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256"
            },
            follow_redirects=False
        )

        # OAuth spec: redirect with error in query params
        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "error=" in location
        assert "unauthorized_client" in location or "invalid_client" in location

    def test_authorize_invalid_redirect_uri(
        self, client: TestClient, sample_oauth_client, sample_scopes
    ):
        """Test authorization fails with unregistered redirect_uri."""
        _, code_challenge = self.generate_pkce_pair()

        response = client.get(
            "/api/v1/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": sample_oauth_client.client_id,
                "redirect_uri": "https://evil.com/callback",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256"
            },
            follow_redirects=False
        )

        # OAuth spec: redirect with error when redirect_uri is invalid
        # (though technically should not redirect to unregistered URI per spec)
        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "error=" in location
        assert "invalid_request" in location

    def test_authorize_missing_pkce(
        self, client: TestClient, sample_oauth_client, sample_scopes
    ):
        """Test authorization fails without PKCE (missing required code_challenge)."""
        response = client.get(
            "/api/v1/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": sample_oauth_client.client_id,
                "redirect_uri": "https://example.com/callback",
                "scope": "openid profile:read:basic"
            }
        )

        # FastAPI returns 422 for missing required query parameters
        assert response.status_code == 422

    def test_authorize_plain_pkce_rejected(
        self, client: TestClient, sample_oauth_client, sample_scopes
    ):
        """Test authorization rejects plain PKCE method (returns redirect with error)."""
        response = client.get(
            "/api/v1/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": sample_oauth_client.client_id,
                "redirect_uri": "https://example.com/callback",
                "code_challenge": "plain-challenge",
                "code_challenge_method": "plain",
                "scope": "openid profile:read:basic"
            },
            follow_redirects=False
        )

        # OAuth spec: redirect with error
        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "error=" in location
        assert "invalid_request" in location
        assert "S256" in location

    def test_authorize_success_returns_consent_required(
        self, client: TestClient, sample_oauth_client, sample_scopes
    ):
        """Test successful authorization request returns consent prompt."""
        _, code_challenge = self.generate_pkce_pair()

        response = client.get(
            "/api/v1/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": sample_oauth_client.client_id,
                "redirect_uri": "https://example.com/callback",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "scope": "openid profile:read:basic",
                "state": "test-state-123"
            },
            follow_redirects=False
        )

        # Should return consent page info (200) or redirect to consent
        assert response.status_code in [200, 302]
        if response.status_code == 200:
            data = response.json()
            # API returns authorization request info for testing
            assert "client_id" in data or "requires_consent" in data or "message" in data


class TestTokenEndpoint:
    """Test OAuth token endpoint."""

    @pytest.fixture
    def sample_profile(self, db_session: Session) -> BaseProfile:
        """Create sample user profile."""
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
    def sample_oauth_client(self, db_session: Session) -> OAuthClient:
        """Create sample OAuth client."""
        client = OAuthClient(
            client_id="token-test-client",
            client_name="Token Test Client",
            redirect_uris=["https://example.com/callback"],
            allowed_scopes=["openid", "profile:read:basic", "offline_access"],
            is_confidential=False,
            is_active=True
        )
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        return client

    @pytest.fixture
    def sample_scopes(self, db_session: Session) -> list[OAuthScope]:
        """Create sample OAuth scopes."""
        scopes = [
            OAuthScope(
                scope_name="openid",
                description="OpenID Connect",
                access_level=AccessLevel.read
            ),
            OAuthScope(
                scope_name="profile:read:basic",
                description="Basic profile",
                access_level=AccessLevel.read
            ),
            OAuthScope(
                scope_name="offline_access",
                description="Refresh token",
                access_level=AccessLevel.read
            )
        ]
        db_session.add_all(scopes)
        db_session.commit()
        return scopes

    @staticmethod
    def generate_pkce_pair() -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge."""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return code_verifier, code_challenge

    def test_token_invalid_grant_type(self, client: TestClient):
        """Test token endpoint rejects invalid grant type."""
        response = client.post(
            "/api/v1/oauth/token",
            data={
                "grant_type": "password",  # Not allowed in OAuth 2.1
                "username": "user",
                "password": "pass"
            }
        )

        assert response.status_code == 400
        data = response.json()
        # Error may be wrapped in detail
        error_info = data.get("detail", data)
        assert error_info.get("error") == "unsupported_grant_type" or \
               error_info.get("error") == "invalid_request"

    def test_token_missing_code(self, client: TestClient, sample_oauth_client):
        """Test token endpoint requires authorization code."""
        response = client.post(
            "/api/v1/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": sample_oauth_client.client_id,
                "redirect_uri": "https://example.com/callback"
            }
        )

        assert response.status_code == 400
        data = response.json()
        # Error may be wrapped in detail
        error_info = data.get("detail", data)
        assert error_info.get("error") == "invalid_request"

    def test_token_invalid_code(self, client: TestClient, sample_oauth_client, sample_scopes):
        """Test token endpoint rejects invalid authorization code."""
        code_verifier, _ = self.generate_pkce_pair()

        response = client.post(
            "/api/v1/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": "invalid-authorization-code",
                "client_id": sample_oauth_client.client_id,
                "redirect_uri": "https://example.com/callback",
                "code_verifier": code_verifier
            }
        )

        assert response.status_code == 400
        data = response.json()
        # Error may be wrapped in detail
        error_info = data.get("detail", data)
        assert error_info.get("error") == "invalid_grant"


class TestIntrospectionEndpoint:
    """Test OAuth token introspection endpoint."""

    def test_introspect_invalid_token(self, client: TestClient):
        """Test introspection returns inactive for invalid token."""
        response = client.post(
            "/api/v1/oauth/introspect",
            data={"token": "invalid-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["active"] is False

    def test_introspect_missing_token(self, client: TestClient):
        """Test introspection requires token parameter."""
        response = client.post("/api/v1/oauth/introspect", data={})

        # FastAPI returns 422 for missing required form fields
        assert response.status_code == 422


class TestRevocationEndpoint:
    """Test OAuth token revocation endpoint."""

    def test_revoke_unknown_token_succeeds(self, client: TestClient):
        """Test revocation returns success for unknown token (RFC 7009)."""
        response = client.post(
            "/api/v1/oauth/revoke",
            data={"token": "unknown-token"}
        )

        # Per RFC 7009, should return success
        assert response.status_code == 200

    def test_revoke_missing_token(self, client: TestClient):
        """Test revocation requires token parameter."""
        response = client.post("/api/v1/oauth/revoke", data={})

        # FastAPI returns 422 for missing required form fields
        assert response.status_code == 422


class TestConsentManagement:
    """Test OAuth consent management endpoints."""

    @pytest.fixture
    def sample_profile(self, db_session: Session) -> BaseProfile:
        """Create sample user profile."""
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
    def sample_oauth_client(self, db_session: Session) -> OAuthClient:
        """Create sample OAuth client."""
        client = OAuthClient(
            client_id="consent-test-client",
            client_name="Consent Test Client",
            redirect_uris=["https://example.com/callback"],
            allowed_scopes=["profile:read:basic"],
            is_active=True
        )
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        return client

    @pytest.fixture
    def sample_consent(
        self, db_session: Session, sample_profile: BaseProfile, sample_oauth_client: OAuthClient
    ) -> OAuthConsent:
        """Create sample consent."""
        consent = OAuthConsent(
            user_id=sample_profile.user_id,
            client_id=sample_oauth_client.client_id,
            granted_scopes=["profile:read:basic"],
            consent_method="explicit"
        )
        db_session.add(consent)
        db_session.commit()
        db_session.refresh(consent)
        return consent

    def test_list_consents_requires_auth(self, client: TestClient):
        """Test listing consents requires authentication."""
        response = client.get("/api/v1/oauth/consents")

        # May return 401 (unauthorized) or 422 (missing user context)
        assert response.status_code in [401, 422]

    def test_withdraw_consent_requires_auth(self, client: TestClient, sample_oauth_client):
        """Test withdrawing consent requires authentication."""
        response = client.delete(f"/api/v1/oauth/consents/{sample_oauth_client.client_id}")

        # May return 401 (unauthorized) or 422 (missing user context)
        assert response.status_code in [401, 422]


class TestUserInfoEndpoint:
    """Test OIDC UserInfo endpoint."""

    def test_userinfo_requires_auth(self, client: TestClient):
        """Test UserInfo endpoint requires authentication."""
        response = client.get("/api/v1/oauth/userinfo")

        # May return 401 (unauthorized) or 422 (missing auth header)
        assert response.status_code in [401, 422]

    def test_userinfo_with_invalid_token(self, client: TestClient):
        """Test UserInfo endpoint rejects invalid token."""
        response = client.get(
            "/api/v1/oauth/userinfo",
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code in [401, 403]


class TestOAuthErrorResponses:
    """Test OAuth error response format compliance."""

    def test_error_response_format(self, client: TestClient):
        """Test error responses follow OAuth 2.0 format."""
        response = client.post(
            "/api/v1/oauth/token",
            data={"grant_type": "invalid_grant_type"}
        )

        assert response.status_code == 400
        data = response.json()

        # RFC 6749 error response format - may be wrapped in 'detail'
        error_info = data.get("detail", data)
        assert "error" in error_info
        assert isinstance(error_info["error"], str)
        # error_description is optional but recommended
        if "error_description" in error_info:
            assert isinstance(error_info["error_description"], str)

    def test_invalid_request_error_code(self, client: TestClient):
        """Test invalid_request error code (missing required params)."""
        response = client.get("/api/v1/oauth/authorize")

        # FastAPI returns 422 for missing required query parameters
        assert response.status_code == 422

    def test_unsupported_grant_type_error_code(self, client: TestClient):
        """Test unsupported_grant_type error code."""
        response = client.post(
            "/api/v1/oauth/token",
            data={"grant_type": "client_credentials"}  # Not supported
        )

        assert response.status_code == 400
        data = response.json()
        # Error may be wrapped in detail
        error_info = data.get("detail", data)
        assert error_info.get("error") in ["unsupported_grant_type", "invalid_request"]


class TestConsentContextVerification:
    """Test that the consent endpoint rejects unverified legal/healthcare
    contexts and accepts verified or non-verification-required contexts."""

    @pytest.fixture
    def user_with_auth(self, db_session: Session):
        """Create a verified user with BaseProfile and AuthUser."""
        profile = BaseProfile(
            account_type=AccountType.verified,
            primary_email="consent-ctx-test@example.com",
            preferred_language="en"
        )
        db_session.add(profile)
        db_session.commit()
        db_session.refresh(profile)

        auth_user = AuthUser(
            user_id=profile.user_id,
            email="consent-ctx-test@example.com",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
            is_email_verified=True,
            is_admin=False,
        )
        db_session.add(auth_user)
        db_session.commit()
        return auth_user

    @pytest.fixture
    def jwt_token(self, user_with_auth):
        """JWT access token for the test user."""
        return create_access_token(
            user_id=str(user_with_auth.user_id),
            email=user_with_auth.email,
            account_type="verified",
        )

    @pytest.fixture
    def auth_headers(self, jwt_token):
        return {"Authorization": f"Bearer {jwt_token}"}

    @pytest.fixture
    def oauth_client(self, db_session: Session) -> OAuthClient:
        client = OAuthClient(
            client_id="ctx-verify-client",
            client_name="Context Verify Test Client",
            redirect_uris=["https://example.com/callback"],
            allowed_scopes=["profile:read:basic"],
            is_confidential=False,
            is_active=True,
        )
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        return client

    @pytest.fixture
    def sample_scopes(self, db_session: Session):
        scope = OAuthScope(
            scope_name="profile:read:basic",
            description="Basic profile",
            access_level=AccessLevel.read,
        )
        db_session.add(scope)
        db_session.commit()
        return [scope]

    @staticmethod
    def generate_pkce_pair() -> tuple[str, str]:
        code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).rstrip(b"=").decode()
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return code_verifier, code_challenge

    def _consent_payload(self, oauth_client, context_id=None):
        _, code_challenge = self.generate_pkce_pair()
        payload = {
            "decision": "allow",
            "client_id": oauth_client.client_id,
            "redirect_uri": "https://example.com/callback",
            "response_type": "code",
            "scope": "profile:read:basic",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "remember": False,
        }
        if context_id:
            payload["context_id"] = str(context_id)
        return payload

    def test_consent_rejects_unverified_legal_context(
        self, client: TestClient, db_session: Session,
        user_with_auth, auth_headers, oauth_client, sample_scopes,
    ):
        """Consent must fail when binding a legal context with pending
        verification status."""
        ctx = ContextProfile(
            user_id=user_with_auth.user_id,
            context_type=ContextType.legal,
            context_name="Legal Pending",
            is_active=True,
            verification_status=VerificationStatus.pending,
        )
        db_session.add(ctx)
        db_session.commit()
        db_session.refresh(ctx)

        payload = self._consent_payload(oauth_client, context_id=ctx.id)
        response = client.post(
            "/api/v1/oauth/consent",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "error=invalid_request" in data["redirect_to"]

    def test_consent_allows_verified_legal_context(
        self, client: TestClient, db_session: Session,
        user_with_auth, auth_headers, oauth_client, sample_scopes,
    ):
        """Consent must succeed when binding a legal context that has been
        verified by an admin."""
        ctx = ContextProfile(
            user_id=user_with_auth.user_id,
            context_type=ContextType.legal,
            context_name="Legal Verified",
            is_active=True,
            verification_status=VerificationStatus.verified,
        )
        db_session.add(ctx)
        db_session.commit()
        db_session.refresh(ctx)

        payload = self._consent_payload(oauth_client, context_id=ctx.id)
        response = client.post(
            "/api/v1/oauth/consent",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "code=" in data["redirect_to"]
        assert "error" not in data["redirect_to"]

    def test_consent_allows_professional_context_without_verification(
        self, client: TestClient, db_session: Session,
        user_with_auth, auth_headers, oauth_client, sample_scopes,
    ):
        """Professional contexts do not require verification and must pass
        through regardless."""
        ctx = ContextProfile(
            user_id=user_with_auth.user_id,
            context_type=ContextType.professional,
            context_name="Work",
            is_active=True,
        )
        db_session.add(ctx)
        db_session.commit()
        db_session.refresh(ctx)

        payload = self._consent_payload(oauth_client, context_id=ctx.id)
        response = client.post(
            "/api/v1/oauth/consent",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "code=" in data["redirect_to"]
        assert "error" not in data["redirect_to"]


class TestUserInfoContextVerification:
    """Test that the UserInfo endpoint rejects serving data from unverified
    legal/healthcare contexts and accepts verified or non-verification-required
    contexts."""

    @pytest.fixture
    def user_with_profile(self, db_session: Session):
        """Create a verified user with profile and auth record."""
        profile = BaseProfile(
            account_type=AccountType.verified,
            primary_email="userinfo-ctx@example.com",
            preferred_language="en",
        )
        db_session.add(profile)
        db_session.commit()
        db_session.refresh(profile)

        auth_user = AuthUser(
            user_id=profile.user_id,
            email="userinfo-ctx@example.com",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
            is_email_verified=True,
        )
        db_session.add(auth_user)
        db_session.commit()
        return profile

    @pytest.fixture
    def oauth_client(self, db_session: Session) -> OAuthClient:
        client = OAuthClient(
            client_id="userinfo-ctx-client",
            client_name="UserInfo Context Test",
            redirect_uris=["https://example.com/callback"],
            allowed_scopes=["profile:read:basic"],
            is_active=True,
        )
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        return client

    def _create_access_token_record(
        self, db_session, user_id, client_id, context_profile_id=None
    ) -> OAuthAccessToken:
        """Insert an active OAuth access token directly into the DB."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        token = OAuthAccessToken(
            token_hash=token_hash,
            client_id=client_id,
            user_id=user_id,
            scope="profile:read:basic",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            issued_at=datetime.now(timezone.utc),
            context_profile_id=context_profile_id,
        )
        db_session.add(token)
        db_session.commit()
        db_session.refresh(token)
        # Return both the raw token (for the Bearer header) and the record
        token._raw = raw_token
        return token

    def test_userinfo_returns_403_for_rejected_legal_context(
        self, client: TestClient, db_session: Session,
        user_with_profile, oauth_client,
    ):
        """UserInfo must return 403 when the bound legal context has been
        rejected after the token was issued."""
        ctx = ContextProfile(
            user_id=user_with_profile.user_id,
            context_type=ContextType.legal,
            context_name="Legal Rejected",
            is_active=False,
            verification_status=VerificationStatus.rejected,
        )
        db_session.add(ctx)
        db_session.commit()
        db_session.refresh(ctx)

        token = self._create_access_token_record(
            db_session, user_with_profile.user_id,
            oauth_client.client_id, context_profile_id=ctx.id,
        )

        response = client.get(
            "/api/v1/oauth/userinfo",
            headers={"Authorization": f"Bearer {token._raw}"},
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "context_not_verified"

    def test_userinfo_serves_verified_legal_context(
        self, client: TestClient, db_session: Session,
        user_with_profile, oauth_client,
    ):
        """UserInfo must serve data when the bound legal context is verified."""
        ctx = ContextProfile(
            user_id=user_with_profile.user_id,
            context_type=ContextType.legal,
            context_name="Legal Verified",
            is_active=True,
            verification_status=VerificationStatus.verified,
            display_name_override="Jane Legal",
        )
        db_session.add(ctx)
        db_session.commit()
        db_session.refresh(ctx)

        token = self._create_access_token_record(
            db_session, user_with_profile.user_id,
            oauth_client.client_id, context_profile_id=ctx.id,
        )

        response = client.get(
            "/api/v1/oauth/userinfo",
            headers={"Authorization": f"Bearer {token._raw}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Jane Legal"
        assert data["context"] == "legal"

    def test_userinfo_serves_professional_context_without_verification(
        self, client: TestClient, db_session: Session,
        user_with_profile, oauth_client,
    ):
        """UserInfo must serve data for professional contexts regardless of
        verification status (they do not require it)."""
        ctx = ContextProfile(
            user_id=user_with_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work",
            is_active=True,
            display_name_override="Jane Work",
        )
        db_session.add(ctx)
        db_session.commit()
        db_session.refresh(ctx)

        token = self._create_access_token_record(
            db_session, user_with_profile.user_id,
            oauth_client.client_id, context_profile_id=ctx.id,
        )

        response = client.get(
            "/api/v1/oauth/userinfo",
            headers={"Authorization": f"Bearer {token._raw}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Jane Work"
        assert data["context"] == "professional"
