"""Integration tests for social authentication endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.main import app
from src.models.auth import AuthUser
from src.models.profile import BaseProfile, AccountType
from src.repositories.auth_repository import AuthRepository
from src.repositories.profile_repository import ProfileRepository


class TestSocialAuthAuthorizeEndpoint:
    """Test POST /api/v1/auth/social/{provider}/authorize endpoint."""

    @patch('src.core.config.settings.GOOGLE_CLIENT_SECRET', 'test-client-secret')
    @patch('src.core.config.settings.GOOGLE_CLIENT_ID', 'test-client-id')
    def test_google_authorize_success(self, client):
        """Test successful authorization URL generation for Google."""
        response = client.post("/api/v1/auth/social/google/authorize")

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert "code_verifier" in data
        assert "accounts.google.com" in data["authorization_url"]
        assert "code_challenge" in data["authorization_url"]

    def test_invalid_provider(self, client):
        """Test authorization fails with unsupported provider."""
        response = client.post("/api/v1/auth/social/github/authorize")

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "invalid_provider"

    @patch('src.core.config.settings.GOOGLE_CLIENT_ID', None)
    def test_unconfigured_provider(self, client):
        """Test authorization fails when OAuth credentials not configured."""
        response = client.post("/api/v1/auth/social/google/authorize")

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "oauth_not_configured"


class TestSocialAuthCallbackEndpoint:
    """Test GET /api/v1/auth/social/{provider}/callback endpoint."""

    @patch('src.services.social_auth_service.SocialAuthService.exchange_code_for_token')
    @patch('src.services.social_auth_service.SocialAuthService.verify_google_id_token')
    def test_callback_new_user_success(
        self,
        mock_verify_token,
        mock_exchange_code,
        client,
        db_session
    ):
        """Test successful OAuth callback with new user creation."""
        mock_exchange_code.return_value = {
            "access_token": "google-access-token",
            "id_token": "google-id-token",
            "expires_in": 3600
        }

        mock_verify_token.return_value = {
            "sub": "google-user-123456",
            "email": "newuser@gmail.com",
            "name": "New User",
            "email_verified": True
        }

        response = client.get(
            "/api/v1/auth/social/google/callback",
            params={
                "code": "auth-code-123",
                "state": "state-value",
                "code_verifier": "verifier-value",
                "expected_state": "state-value"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["email"] == "newuser@gmail.com"
        assert data["is_email_verified"] is True
        assert data["account_type"] == "unverified"

        auth_repo = AuthRepository(db_session)
        user = auth_repo.get_by_provider("google", "google-user-123456")
        assert user is not None
        assert user.email == "newuser@gmail.com"
        assert user.provider == "google"
        assert user.provider_id == "google-user-123456"

    @patch('src.services.social_auth_service.SocialAuthService.exchange_code_for_token')
    @patch('src.services.social_auth_service.SocialAuthService.verify_google_id_token')
    def test_callback_existing_user_success(
        self,
        mock_verify_token,
        mock_exchange_code,
        client,
        db_session
    ):
        """Test successful OAuth callback with existing user login."""
        profile_repo = ProfileRepository(db_session)
        profile = profile_repo.create_profile(
            account_type=AccountType.verified,
            primary_email="existing@gmail.com",
            preferred_language="en"
        )

        auth_repo = AuthRepository(db_session)
        auth_repo.create_user(
            email="existing@gmail.com",
            password_hash="not-used",
            user_id=str(profile.user_id),
            is_email_verified=True,
            provider="google",
            provider_id="google-user-existing"
        )
        db_session.commit()

        mock_exchange_code.return_value = {
            "access_token": "google-access-token",
            "id_token": "google-id-token"
        }

        mock_verify_token.return_value = {
            "sub": "google-user-existing",
            "email": "existing@gmail.com",
            "name": "Existing User",
            "email_verified": True
        }

        response = client.get(
            "/api/v1/auth/social/google/callback",
            params={
                "code": "auth-code-456",
                "state": "state-value",
                "code_verifier": "verifier-value",
                "expected_state": "state-value"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "existing@gmail.com"
        assert data["is_email_verified"] is True

    @patch('src.services.social_auth_service.SocialAuthService.exchange_code_for_token')
    @patch('src.services.social_auth_service.SocialAuthService.verify_google_id_token')
    def test_callback_soft_deleted_user_recoverable(
        self,
        mock_verify_token,
        mock_exchange_code,
        client,
        db_session
    ):
        """Test OAuth callback with soft-deleted user returns ACCOUNT_RECOVERABLE."""
        profile_repo = ProfileRepository(db_session)
        profile = profile_repo.create_profile(
            account_type=AccountType.verified,
            primary_email="deleted@gmail.com",
            preferred_language="en"
        )

        auth_repo = AuthRepository(db_session)
        auth_user = auth_repo.create_user(
            email="deleted@gmail.com",
            password_hash="not-used",
            user_id=str(profile.user_id),
            is_email_verified=True,
            provider="google",
            provider_id="google-user-deleted"
        )

        auth_repo.soft_delete(str(profile.user_id))
        db_session.commit()

        deleted_user = auth_repo.get_by_provider_including_deleted("google", "google-user-deleted")
        assert deleted_user is not None
        assert deleted_user.deleted_at is not None

        mock_exchange_code.return_value = {
            "access_token": "google-access-token",
            "id_token": "google-id-token"
        }

        mock_verify_token.return_value = {
            "sub": "google-user-deleted",
            "email": "deleted@gmail.com",
            "name": "Deleted User",
            "email_verified": True
        }

        response = client.get(
            "/api/v1/auth/social/google/callback",
            params={
                "code": "auth-code-789",
                "state": "state-value",
                "code_verifier": "verifier-value",
                "expected_state": "state-value"
            }
        )

        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["code"] == "ACCOUNT_RECOVERABLE"
        assert "permanent_deletion_date" in data["detail"]
        assert data["detail"]["restore_endpoint"] == "/api/v1/auth/restore-account"

        permanent_date = datetime.fromisoformat(
            data["detail"]["permanent_deletion_date"].replace("Z", "+00:00")
        )
        assert permanent_date > datetime.now(timezone.utc)

    @patch('src.services.social_auth_service.SocialAuthService.exchange_code_for_token')
    @patch('src.services.social_auth_service.SocialAuthService.verify_google_id_token')
    def test_callback_account_linking_required(
        self,
        mock_verify_token,
        mock_exchange_code,
        client,
        db_session
    ):
        """Test OAuth callback with existing email/password account requires linking."""
        profile_repo = ProfileRepository(db_session)
        profile = profile_repo.create_profile(
            account_type=AccountType.verified,
            primary_email="existing@example.com",
            preferred_language="en"
        )

        auth_repo = AuthRepository(db_session)
        auth_repo.create_user(
            email="existing@example.com",
            password_hash="argon2-hash-here",
            user_id=str(profile.user_id),
            is_email_verified=True,
            provider=None,  # Email/password auth
            provider_id=None
        )
        db_session.commit()

        mock_exchange_code.return_value = {
            "access_token": "google-access-token",
            "id_token": "google-id-token"
        }

        mock_verify_token.return_value = {
            "sub": "google-user-new",
            "email": "existing@example.com",
            "name": "Google User",
            "email_verified": True
        }

        response = client.get(
            "/api/v1/auth/social/google/callback",
            params={
                "code": "auth-code-abc",
                "state": "state-value",
                "code_verifier": "verifier-value",
                "expected_state": "state-value"
            }
        )

        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["code"] == "account_linking_required"
        assert "password" in data["detail"]["message"].lower()

    def test_callback_invalid_state(self, client):
        """Test callback fails with state parameter mismatch (CSRF protection)."""
        response = client.get(
            "/api/v1/auth/social/google/callback",
            params={
                "code": "auth-code",
                "state": "wrong-state",
                "code_verifier": "verifier",
                "expected_state": "correct-state"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "invalid_state"

    @patch('src.services.social_auth_service.SocialAuthService.exchange_code_for_token')
    def test_callback_missing_id_token(
        self,
        mock_exchange_code,
        client
    ):
        """Test callback fails when provider doesn't return ID token."""
        mock_exchange_code.return_value = {
            "access_token": "google-access-token",
            "expires_in": 3600
        }

        response = client.get(
            "/api/v1/auth/social/google/callback",
            params={
                "code": "auth-code",
                "state": "state-value",
                "code_verifier": "verifier",
                "expected_state": "state-value"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "missing_id_token"


class TestSoftDeletedOAuthUserEdgeCases:
    """Test edge cases for soft-deleted OAuth users."""

    @patch('src.services.social_auth_service.SocialAuthService.exchange_code_for_token')
    @patch('src.services.social_auth_service.SocialAuthService.verify_google_id_token')
    def test_soft_deleted_user_prevents_duplicate_insert(
        self,
        mock_verify_token,
        mock_exchange_code,
        client,
        db_session
    ):
        """
        Test that soft-deleted OAuth user prevents duplicate key violation.

        This test reproduces the bug: user deletes account, then tries to
        sign up again with same Google account. Without the fix, this would
        cause a UniqueViolation on (provider, provider_id).
        """
        profile_repo = ProfileRepository(db_session)
        profile = profile_repo.create_profile(
            account_type=AccountType.verified,
            primary_email="testuser@gmail.com",
            preferred_language="en"
        )

        auth_repo = AuthRepository(db_session)
        auth_repo.create_user(
            email="testuser@gmail.com",
            password_hash="not-used",
            user_id=str(profile.user_id),
            is_email_verified=True,
            provider="google",
            provider_id="107311201951144540851"  # Real provider_id from error
        )
        db_session.commit()

        auth_repo.soft_delete(str(profile.user_id))
        db_session.commit()

        deleted_user = auth_repo.get_by_provider_including_deleted(
            "google",
            "107311201951144540851"
        )
        assert deleted_user is not None
        assert deleted_user.deleted_at is not None

        mock_exchange_code.return_value = {
            "access_token": "google-access-token",
            "id_token": "google-id-token"
        }

        mock_verify_token.return_value = {
            "sub": "107311201951144540851",  # Same provider_id
            "email": "testuser@gmail.com",
            "name": "Test User",
            "email_verified": True
        }

        response = client.get(
            "/api/v1/auth/social/google/callback",
            params={
                "code": "auth-code",
                "state": "state-value",
                "code_verifier": "verifier",
                "expected_state": "state-value"
            }
        )

        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["code"] == "ACCOUNT_RECOVERABLE"
        assert "permanent_deletion_date" in data["detail"]

        all_users = db_session.query(AuthUser).filter_by(
            provider="google",
            provider_id="107311201951144540851"
        ).all()
        assert len(all_users) == 1  # Only the soft-deleted user
        assert all_users[0].deleted_at is not None

    @patch('src.services.social_auth_service.SocialAuthService.exchange_code_for_token')
    @patch('src.services.social_auth_service.SocialAuthService.verify_google_id_token')
    def test_expired_soft_deleted_user_allows_new_registration(
        self,
        mock_verify_token,
        mock_exchange_code,
        client,
        db_session
    ):
        """
        Test that expired soft-deleted OAuth user allows new registration.

        After 30-day grace period, the old account should be purged and
        new registration should succeed.
        """
        profile_repo = ProfileRepository(db_session)
        profile = profile_repo.create_profile(
            account_type=AccountType.verified,
            primary_email="expired@gmail.com",
            preferred_language="en"
        )

        auth_repo = AuthRepository(db_session)
        auth_user = auth_repo.create_user(
            email="expired@gmail.com",
            password_hash="not-used",
            user_id=str(profile.user_id),
            is_email_verified=True,
            provider="google",
            provider_id="google-user-expired"
        )

        auth_user.deleted_at = datetime.now(timezone.utc) - timedelta(days=31)
        db_session.commit()

        mock_exchange_code.return_value = {
            "access_token": "google-access-token",
            "id_token": "google-id-token"
        }

        mock_verify_token.return_value = {
            "sub": "google-user-expired",
            "email": "expired@gmail.com",
            "name": "Expired User",
            "email_verified": True
        }

        response = client.get(
            "/api/v1/auth/social/google/callback",
            params={
                "code": "auth-code",
                "state": "state-value",
                "code_verifier": "verifier",
                "expected_state": "state-value"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "expired@gmail.com"
        assert "access_token" in data
        assert "refresh_token" in data
