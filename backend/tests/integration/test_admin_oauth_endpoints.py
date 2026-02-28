"""
Integration tests for admin OAuth client management endpoints.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import create_access_token
from src.main import app
from src.models.auth import AuthUser
from src.models.oauth import OAuthClient


class TestAdminOAuthEndpoints:
    """Integration tests for admin OAuth endpoints."""

    @pytest.fixture
    def client(self, db_session: Session):
        """Create a test client with database dependency override."""

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        yield TestClient(app)
        app.dependency_overrides.clear()

    @pytest.fixture
    def admin_user(self, db_session: Session):
        """Create an admin user for testing."""
        from src.models.profile import AccountType, BaseProfile

        # Create base profile first
        profile = BaseProfile(
            user_id="00000000-0000-0000-0000-000000000099",
            account_type=AccountType.verified,
            primary_email="test.admin@example.com",
            preferred_language="en",
        )
        db_session.add(profile)
        db_session.commit()

        # Create admin auth user
        admin = AuthUser(
            user_id="00000000-0000-0000-0000-000000000099",
            email="test.admin@example.com",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
            is_email_verified=True,
            is_admin=True,
        )
        db_session.add(admin)
        db_session.commit()
        return admin

    @pytest.fixture
    def regular_user(self, db_session: Session):
        """Create a regular (non-admin) user for testing."""
        from src.models.profile import AccountType, BaseProfile

        profile = BaseProfile(
            user_id="00000000-0000-0000-0000-000000000098",
            account_type=AccountType.verified,
            primary_email="regular.user@example.com",
            preferred_language="en",
        )
        db_session.add(profile)
        db_session.commit()

        user = AuthUser(
            user_id="00000000-0000-0000-0000-000000000098",
            email="regular.user@example.com",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
            is_email_verified=True,
            is_admin=False,
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def admin_token(self, admin_user):
        """Generate access token for admin user."""
        return create_access_token(
            user_id=str(admin_user.user_id), email=admin_user.email, account_type="verified"
        )

    @pytest.fixture
    def regular_token(self, regular_user):
        """Generate access token for regular user."""
        return create_access_token(
            user_id=str(regular_user.user_id), email=regular_user.email, account_type="verified"
        )

    @pytest.fixture
    def sample_oauth_client(self, db_session: Session):
        """Create a sample OAuth client for testing."""

        client = OAuthClient(
            client_id="test-client-001",
            client_name="Test Client",
            client_description="A test OAuth client",
            redirect_uris=["https://example.com/callback"],
            allowed_scopes=["profile:read:basic"],
            is_confidential=False,
            is_active=True,
            is_first_party=False,
        )
        db_session.add(client)
        db_session.commit()
        return client

    def test_create_client_as_admin(self, client: TestClient, admin_token: str):
        """Test creating an OAuth client as admin."""
        response = client.post(
            "/api/v1/admin/oauth/clients",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "client_id": "new-test-client",
                "client_name": "New Test Client",
                "client_description": "Created via test",
                "redirect_uris": ["https://newapp.example.com/callback"],
                "allowed_scopes": ["profile:read:basic", "profile:read:email"],
                "is_confidential": True,
                "is_first_party": False,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["client_id"] == "new-test-client"
        assert data["client_name"] == "New Test Client"
        assert data["is_confidential"] is True
        # Secret should be returned on creation
        assert "client_secret" in data
        assert data["client_secret"] is not None

    def test_create_client_as_non_admin_fails(self, client: TestClient, regular_token: str):
        """Test that non-admin cannot create OAuth client."""
        response = client.post(
            "/api/v1/admin/oauth/clients",
            headers={"Authorization": f"Bearer {regular_token}"},
            json={
                "client_id": "unauthorized-client",
                "client_name": "Unauthorized",
                "redirect_uris": ["https://unauthorized.com/callback"],
            },
        )

        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_create_client_without_auth_fails(self, client: TestClient):
        """Test that unauthenticated request fails."""
        response = client.post(
            "/api/v1/admin/oauth/clients",
            json={
                "client_id": "no-auth-client",
                "client_name": "No Auth",
                "redirect_uris": ["https://noauth.com/callback"],
            },
        )

        assert response.status_code == 401

    def test_create_duplicate_client_fails(
        self, client: TestClient, admin_token: str, sample_oauth_client: OAuthClient
    ):
        """Test that creating duplicate client_id fails."""
        response = client.post(
            "/api/v1/admin/oauth/clients",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "client_id": sample_oauth_client.client_id,  # Duplicate
                "client_name": "Duplicate Client",
                "redirect_uris": ["https://duplicate.com/callback"],
            },
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_list_clients_as_admin(
        self, client: TestClient, admin_token: str, sample_oauth_client: OAuthClient
    ):
        """Test listing OAuth clients as admin."""
        response = client.get(
            "/api/v1/admin/oauth/clients", headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "clients" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_get_client_as_admin(
        self, client: TestClient, admin_token: str, sample_oauth_client: OAuthClient
    ):
        """Test getting a specific OAuth client as admin."""
        response = client.get(
            f"/api/v1/admin/oauth/clients/{sample_oauth_client.client_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["client_id"] == sample_oauth_client.client_id
        assert data["client_name"] == sample_oauth_client.client_name
        # Secret should NOT be in regular response
        assert "client_secret" not in data or data.get("client_secret") is None

    def test_get_nonexistent_client_fails(self, client: TestClient, admin_token: str):
        """Test getting a client that doesn't exist."""
        response = client.get(
            "/api/v1/admin/oauth/clients/nonexistent-client-xyz",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404

    def test_update_client_as_admin(
        self, client: TestClient, admin_token: str, sample_oauth_client: OAuthClient
    ):
        """Test updating an OAuth client as admin."""
        response = client.patch(
            f"/api/v1/admin/oauth/clients/{sample_oauth_client.client_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "client_name": "Updated Test Client",
                "client_description": "Updated description",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["client_name"] == "Updated Test Client"
        assert data["client_description"] == "Updated description"

    def test_delete_client_as_admin(
        self, client: TestClient, admin_token: str, sample_oauth_client: OAuthClient
    ):
        """Test soft-deleting an OAuth client as admin."""
        response = client.delete(
            f"/api/v1/admin/oauth/clients/{sample_oauth_client.client_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 204

        # Verify client is no longer accessible
        get_response = client.get(
            f"/api/v1/admin/oauth/clients/{sample_oauth_client.client_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_response.status_code == 404

    def test_public_client_no_secret(self, client: TestClient, admin_token: str):
        """Test creating a public client (no secret needed)."""
        response = client.post(
            "/api/v1/admin/oauth/clients",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "client_id": "public-spa-client",
                "client_name": "Public SPA Client",
                "redirect_uris": ["https://spa.example.com/callback"],
                "is_confidential": False,  # Public client
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["is_confidential"] is False
        # Public clients don't have secrets
        assert data["client_secret"] is None

    def test_admin_via_env_var(self, client: TestClient, regular_user: AuthUser):
        """Test that user in ADMIN_USER_EMAILS env var gets admin access."""
        # Create token for regular user
        token = create_access_token(
            user_id=str(regular_user.user_id), email=regular_user.email, account_type="verified"
        )

        # Patch settings to include user in admin emails
        with patch("src.api.dependencies.auth.settings") as mock_settings:
            mock_settings.admin_emails = [regular_user.email.lower()]

            response = client.get(
                "/api/v1/admin/oauth/clients", headers={"Authorization": f"Bearer {token}"}
            )

            # Should succeed because user is in env var list
            assert response.status_code == 200
