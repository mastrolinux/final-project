"""Integration tests for soft deletion and account restoration endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import create_access_token, hash_password
from src.main import app
from src.models.auth import AuthUser
from src.models.context import ContextProfile, ContextType
from src.models.profile import AccountType, BaseProfile, IdentityName, NameType, VisibilityLevel


class TestSoftDeletionEndpoints:
    """Tests for privacy deletion and auth restoration endpoints."""

    @pytest.fixture
    def client(self, db_session: Session):
        """Test client with database override."""

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        yield TestClient(app)
        app.dependency_overrides.clear()

    @pytest.fixture
    def user_profile(self, db_session: Session):
        """Create a complete user: profile + auth + name + context."""
        profile = BaseProfile(
            user_id="00000000-0000-0000-0000-000000000070",
            account_type=AccountType.verified,
            legal_name="Deletion Test User",
            primary_email="delete.test@example.com",
            preferred_language="en",
        )
        db_session.add(profile)
        db_session.commit()

        auth_user = AuthUser(
            user_id="00000000-0000-0000-0000-000000000070",
            email="delete.test@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_email_verified=True,
            is_admin=False,
        )
        db_session.add(auth_user)
        db_session.commit()

        name = IdentityName(
            identity_id=profile.user_id,
            name_type=NameType.full_name,
            name_value={"en": "Deletion Test User"},
            is_primary=True,
            is_deprecated=False,
            visibility_level=VisibilityLevel.public,
        )
        db_session.add(name)

        context = ContextProfile(
            user_id=profile.user_id,
            context_type=ContextType.professional,
            context_name="Work",
            is_active=True,
        )
        db_session.add(context)
        db_session.commit()

        return auth_user

    @pytest.fixture
    def user_token(self, user_profile):
        """JWT token for the test user."""
        return create_access_token(
            user_id=str(user_profile.user_id),
            email=user_profile.email,
            account_type="verified",
        )

    def _delete_account(self, client, user_token):
        """Helper: soft-delete the account via API."""
        response = client.post(
            "/api/v1/privacy/deletion-request",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        return response

    def _get_auth_user_raw(self, db_session):
        """Helper: query AuthUser without deleted_at filter."""
        db_session.expire_all()
        stmt = select(AuthUser).where(AuthUser.user_id == "00000000-0000-0000-0000-000000000070")
        result = db_session.execute(stmt)
        return result.scalars().first()

    def test_deletion_request_returns_200(self, client, user_token, user_profile):
        """POST /privacy/deletion-request returns 200 with scheduling info."""
        response = self._delete_account(client, user_token)
        data = response.json()
        assert data["status"] == "scheduled"
        assert "deletion_scheduled_at" in data
        assert "permanent_deletion_date" in data

    def test_deletion_request_requires_authentication(self, client):
        """POST /privacy/deletion-request returns 401 without token."""
        response = client.post("/api/v1/privacy/deletion-request")
        assert response.status_code == 401

    def test_deleted_user_cannot_reauthenticate(self, client, user_token, user_profile):
        """After soft deletion, JWT-authenticated requests return 401."""
        self._delete_account(client, user_token)
        response = client.post(
            "/api/v1/privacy/deletion-request",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 401

    def test_deletion_status_returns_active(self, client, user_token, user_profile):
        """GET /privacy/deletion-status for active account returns 'active'."""
        response = client.get(
            "/api/v1/privacy/deletion-status",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_deletion_status_requires_auth(self, client):
        """GET /privacy/deletion-status returns 401 without token."""
        response = client.get("/api/v1/privacy/deletion-status")
        assert response.status_code == 401

    def test_login_after_deletion_returns_403(self, client, user_token, user_profile):
        """Login attempt for soft-deleted account returns 403 with deletion info."""
        self._delete_account(client, user_token)
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "delete.test@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "ACCOUNT_DELETED"
        assert "deletion_scheduled_at" in data["detail"]
        assert "recovery_info" in data["detail"]

    @patch("src.services.auth_service.send_verification_email")
    def test_register_detects_recoverable_returns_409(
        self, mock_send_email, client, user_token, user_profile
    ):
        """Registration with email of recoverable account returns 409."""
        self._delete_account(client, user_token)
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "delete.test@example.com",
                "password": "AnotherSecure123!",
                "preferred_name": "New User",
            },
        )
        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["code"] == "ACCOUNT_RECOVERABLE"
        assert data["detail"]["account_recoverable"] is True
        assert "restore_endpoint" in data["detail"]

    @patch("src.services.auth_service.send_restoration_email")
    def test_restore_account_returns_202(self, mock_send_email, client, user_token, user_profile):
        """POST /auth/restore-account returns 202 for recoverable account."""
        self._delete_account(client, user_token)
        response = client.post(
            "/api/v1/auth/restore-account",
            json={"email": "delete.test@example.com"},
        )
        assert response.status_code == 202
        mock_send_email.delay.assert_called_once()

    @patch("src.services.auth_service.send_restoration_email")
    def test_restore_account_nonexistent_returns_202(self, mock_send_email, client):
        """POST /auth/restore-account returns 202 for unknown email (enumeration prevention)."""
        response = client.post(
            "/api/v1/auth/restore-account",
            json={"email": "nobody@example.com"},
        )
        assert response.status_code == 202
        mock_send_email.delay.assert_not_called()

    @patch("src.services.auth_service.send_restoration_email")
    def test_restore_confirm_restores_account_returns_200(
        self, mock_send_email, client, user_token, user_profile, db_session
    ):
        """Full restoration: delete, request, retrieve token, confirm, get tokens."""
        self._delete_account(client, user_token)

        # Request restoration
        client.post(
            "/api/v1/auth/restore-account",
            json={"email": "delete.test@example.com"},
        )

        # Retrieve the restoration token from DB
        auth_user = self._get_auth_user_raw(db_session)
        token = auth_user.restoration_token
        assert token is not None

        # Confirm restoration
        response = client.post(
            "/api/v1/auth/restore-account/confirm",
            json={"token": token, "new_password": "RestoredSecure123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "restored_at" in data

    def test_restore_confirm_invalid_token_returns_400(self, client):
        """POST /auth/restore-account/confirm with invalid token returns 400."""
        # Token must be >= 32 chars to pass schema validation
        fake_token = "a" * 43  # secrets.token_urlsafe(32) produces ~43 chars
        response = client.post(
            "/api/v1/auth/restore-account/confirm",
            json={"token": fake_token, "new_password": "SecurePass123!"},
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_RESTORATION_TOKEN"

    @patch("src.services.auth_service.send_restoration_email")
    def test_restore_confirm_expired_grace_returns_410(
        self, mock_send_email, client, user_token, user_profile, db_session
    ):
        """Restoration after grace period expiry returns 410 Gone."""
        self._delete_account(client, user_token)

        # Request restoration to generate token
        client.post(
            "/api/v1/auth/restore-account",
            json={"email": "delete.test@example.com"},
        )

        auth_user = self._get_auth_user_raw(db_session)
        token = auth_user.restoration_token
        auth_user.deleted_at = datetime.now(UTC) - timedelta(days=35)
        db_session.commit()

        # Attempt confirmation
        response = client.post(
            "/api/v1/auth/restore-account/confirm",
            json={"token": token, "new_password": "SecurePass123!"},
        )
        assert response.status_code == 410
        assert response.json()["detail"]["code"] == "ACCOUNT_PERMANENTLY_DELETED"

    @patch("src.services.auth_service.send_restoration_email")
    def test_full_deletion_and_restoration_flow(
        self, mock_send_email, client, user_token, user_profile, db_session
    ):
        """End-to-end: active -> deleted -> restored -> active."""
        headers = {"Authorization": f"Bearer {user_token}"}

        # 1. Verify active status
        response = client.get("/api/v1/privacy/deletion-status", headers=headers)
        assert response.json()["status"] == "active"

        # 2. Request deletion
        response = client.post("/api/v1/privacy/deletion-request", headers=headers)
        assert response.status_code == 200

        # 3. After deletion, JWT auth fails (correct behavior)
        response = client.get("/api/v1/privacy/deletion-status", headers=headers)
        assert response.status_code == 401

        # 4. Login fails with 403 (includes deletion info)
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "delete.test@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 403

        # 5. Request restoration
        client.post(
            "/api/v1/auth/restore-account",
            json={
                "email": "delete.test@example.com",
            },
        )

        # 6. Get token from DB
        auth_user = self._get_auth_user_raw(db_session)
        token = auth_user.restoration_token

        # 7. Confirm restoration
        response = client.post(
            "/api/v1/auth/restore-account/confirm",
            json={
                "token": token,
                "new_password": "RestoredSecure123!",
            },
        )
        assert response.status_code == 200
        new_access_token = response.json()["access_token"]

        # 8. Login with new password succeeds
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "delete.test@example.com",
                "password": "RestoredSecure123!",
            },
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

        # 9. Deletion status is active again
        response = client.get(
            "/api/v1/privacy/deletion-status",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert response.json()["status"] == "active"
