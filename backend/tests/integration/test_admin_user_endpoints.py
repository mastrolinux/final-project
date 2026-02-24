"""
Integration tests for admin user management endpoints.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.core.database import get_db
from src.models.auth import AuthUser
from src.core.security import create_access_token


class TestAdminUserEndpoints:
    """Integration tests for admin user management endpoints."""

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
        from src.models.profile import BaseProfile, AccountType

        profile = BaseProfile(
            user_id="00000000-0000-0000-0000-000000000080",
            account_type=AccountType.verified,
            primary_email="admin.purge@example.com",
            preferred_language="en",
        )
        db_session.add(profile)
        db_session.commit()

        admin = AuthUser(
            user_id="00000000-0000-0000-0000-000000000080",
            email="admin.purge@example.com",
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
        from src.models.profile import BaseProfile, AccountType

        profile = BaseProfile(
            user_id="00000000-0000-0000-0000-000000000081",
            account_type=AccountType.verified,
            primary_email="regular.purge@example.com",
            preferred_language="en",
        )
        db_session.add(profile)
        db_session.commit()

        user = AuthUser(
            user_id="00000000-0000-0000-0000-000000000081",
            email="regular.purge@example.com",
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
            user_id=str(admin_user.user_id),
            email=admin_user.email,
            account_type="verified",
        )

    @pytest.fixture
    def regular_token(self, regular_user):
        """Generate access token for regular user."""
        return create_access_token(
            user_id=str(regular_user.user_id),
            email=regular_user.email,
            account_type="verified",
        )

    @pytest.fixture
    def soft_deleted_user(self, db_session: Session):
        """Create a soft-deleted user for testing."""
        from src.models.profile import BaseProfile, AccountType

        profile = BaseProfile(
            user_id="00000000-0000-0000-0000-000000000082",
            account_type=AccountType.verified,
            primary_email="deleted.user@example.com",
            preferred_language="en",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        db_session.add(profile)
        db_session.commit()

        user = AuthUser(
            user_id="00000000-0000-0000-0000-000000000082",
            email="deleted.user@example.com",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
            is_email_verified=True,
            is_admin=False,
            deleted_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        db_session.add(user)
        db_session.commit()
        return user

    #
    # GET /api/v1/admin/users/soft-deleted
    #

    def test_list_soft_deleted_users_as_admin(
        self, client: TestClient, admin_token: str, soft_deleted_user
    ):
        """Admin can list soft-deleted users."""
        response = client.get(
            "/api/v1/admin/users/soft-deleted",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert data["total"] >= 1
        # Verify the soft-deleted user appears in the list
        emails = [u["email"] for u in data["users"]]
        assert "deleted.user@example.com" in emails

    def test_list_soft_deleted_users_empty(
        self, client: TestClient, admin_token: str
    ):
        """Admin gets empty list when no soft-deleted users exist."""
        response = client.get(
            "/api/v1/admin/users/soft-deleted",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["users"] == []
        assert data["total"] == 0

    def test_list_soft_deleted_users_as_non_admin(
        self, client: TestClient, regular_token: str
    ):
        """Non-admin users cannot list soft-deleted users."""
        response = client.get(
            "/api/v1/admin/users/soft-deleted",
            headers={"Authorization": f"Bearer {regular_token}"},
        )
        assert response.status_code == 403

    def test_list_soft_deleted_users_unauthenticated(
        self, client: TestClient
    ):
        """Unauthenticated requests are rejected."""
        response = client.get("/api/v1/admin/users/soft-deleted")
        assert response.status_code == 401

    def test_list_soft_deleted_users_excludes_active(
        self, client: TestClient, admin_token: str,
        soft_deleted_user, admin_user
    ):
        """Active users do not appear in the soft-deleted list."""
        response = client.get(
            "/api/v1/admin/users/soft-deleted",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = response.json()
        user_ids = [u["user_id"] for u in data["users"]]
        assert str(admin_user.user_id) not in user_ids

    #
    # POST /api/v1/admin/users/purge-expired
    #

    def test_purge_expired_as_admin_none_expired(
        self, client: TestClient, admin_token: str, soft_deleted_user
    ):
        """Admin can trigger purge; returns 0 when no users are expired."""
        # soft_deleted_user was deleted 5 days ago, not yet expired (30 days)
        response = client.post(
            "/api/v1/admin/users/purge-expired",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["purged_count"] == 0

    def test_purge_expired_as_non_admin(
        self, client: TestClient, regular_token: str
    ):
        """Non-admin users cannot trigger purge."""
        response = client.post(
            "/api/v1/admin/users/purge-expired",
            headers={"Authorization": f"Bearer {regular_token}"},
        )
        assert response.status_code == 403

    def test_purge_expired_unauthenticated(self, client: TestClient):
        """Unauthenticated requests are rejected."""
        response = client.post("/api/v1/admin/users/purge-expired")
        assert response.status_code == 401
