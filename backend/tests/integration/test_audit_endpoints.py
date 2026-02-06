"""
Integration Tests for Audit Endpoints

Tests the GET /api/v1/audit/me and GET /api/v1/audit/verify endpoints,
including authentication requirements, pagination, and admin access control.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.core.database import get_db
from src.core.security import create_access_token
from src.models.auth import AuthUser
from src.models.audit import AuditLog, AuditOperation, GENESIS_HASH
from src.models.profile import BaseProfile, AccountType
from src.repositories.audit_repository import AuditRepository


class TestAuditMeEndpoint:
    """Test GET /api/v1/audit/me endpoint."""

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
        """Create a verified user with auth record."""
        profile = BaseProfile(
            user_id="00000000-0000-0000-0000-000000000050",
            account_type=AccountType.verified,
            primary_email="audit.user@example.com",
            preferred_language="en"
        )
        db_session.add(profile)
        db_session.commit()

        auth_user = AuthUser(
            user_id="00000000-0000-0000-0000-000000000050",
            email="audit.user@example.com",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
            is_email_verified=True,
            is_admin=False
        )
        db_session.add(auth_user)
        db_session.commit()
        return auth_user

    @pytest.fixture
    def user_token(self, user_profile):
        """JWT token for the test user."""
        return create_access_token(
            user_id=str(user_profile.user_id),
            email=user_profile.email,
            account_type="verified"
        )

    @pytest.fixture
    def admin_user(self, db_session: Session):
        """Create an admin user."""
        profile = BaseProfile(
            user_id="00000000-0000-0000-0000-000000000051",
            account_type=AccountType.verified,
            primary_email="audit.admin@example.com",
            preferred_language="en"
        )
        db_session.add(profile)
        db_session.commit()

        admin = AuthUser(
            user_id="00000000-0000-0000-0000-000000000051",
            email="audit.admin@example.com",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
            is_email_verified=True,
            is_admin=True
        )
        db_session.add(admin)
        db_session.commit()
        return admin

    @pytest.fixture
    def admin_token(self, admin_user):
        """JWT token for the admin user."""
        return create_access_token(
            user_id=str(admin_user.user_id),
            email=admin_user.email,
            account_type="verified"
        )

    @pytest.fixture
    def sample_audit_logs(self, db_session: Session, user_profile):
        """Create sample audit log entries for the test user."""
        audit_repo = AuditRepository(db_session)
        user_id = user_profile.user_id

        audit_repo.create_log(
            event_type="auth.login.success",
            user_id=user_id,
            actor_id=user_id,
            resource_type="auth_user",
            resource_id=str(user_id),
            operation=AuditOperation.login,
            ip_address="192.168.1.1",
            legal_basis="contract"
        )
        audit_repo.create_log(
            event_type="profile.update",
            user_id=user_id,
            actor_id=user_id,
            resource_type="profile",
            resource_id=str(user_id),
            operation=AuditOperation.update,
            changes={"email": "new@example.com"},
            legal_basis="contract"
        )
        return user_id

    def test_audit_me_requires_authentication(self, client):
        """GET /audit/me returns 401 without token."""
        response = client.get("/api/v1/audit/me")
        assert response.status_code == 401

    def test_audit_me_returns_own_logs(
        self, client, user_token, sample_audit_logs
    ):
        """Authenticated user sees only their own audit entries."""
        response = client.get(
            "/api/v1/audit/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert data["total"] == 2
        assert len(data["entries"]) == 2

    def test_audit_me_does_not_expose_user_agent(
        self, client, user_token, sample_audit_logs
    ):
        """Response excludes user_agent field for privacy."""
        response = client.get(
            "/api/v1/audit/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        data = response.json()
        for entry in data["entries"]:
            assert "user_agent" not in entry

    def test_audit_me_pagination(
        self, client, user_token, sample_audit_logs
    ):
        """Pagination parameters limit and offset work correctly."""
        response = client.get(
            "/api/v1/audit/me?limit=1&offset=0",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        data = response.json()
        assert len(data["entries"]) == 1
        assert data["total"] == 2

    def test_audit_me_empty_for_new_user(self, client, user_token):
        """New user with no audit entries gets empty response."""
        response = client.get(
            "/api/v1/audit/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        data = response.json()
        assert data["total"] == 0
        assert data["entries"] == []


class TestAuditVerifyEndpoint:
    """Test GET /api/v1/audit/verify endpoint."""

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
    def admin_user(self, db_session: Session):
        """Create an admin user."""
        profile = BaseProfile(
            user_id="00000000-0000-0000-0000-000000000052",
            account_type=AccountType.verified,
            primary_email="verify.admin@example.com",
            preferred_language="en"
        )
        db_session.add(profile)
        db_session.commit()

        admin = AuthUser(
            user_id="00000000-0000-0000-0000-000000000052",
            email="verify.admin@example.com",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
            is_email_verified=True,
            is_admin=True
        )
        db_session.add(admin)
        db_session.commit()
        return admin

    @pytest.fixture
    def admin_token(self, admin_user):
        """JWT token for admin."""
        return create_access_token(
            user_id=str(admin_user.user_id),
            email=admin_user.email,
            account_type="verified"
        )

    @pytest.fixture
    def regular_user(self, db_session: Session):
        """Create a non-admin user."""
        profile = BaseProfile(
            user_id="00000000-0000-0000-0000-000000000053",
            account_type=AccountType.verified,
            primary_email="verify.regular@example.com",
            preferred_language="en"
        )
        db_session.add(profile)
        db_session.commit()

        user = AuthUser(
            user_id="00000000-0000-0000-0000-000000000053",
            email="verify.regular@example.com",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
            is_email_verified=True,
            is_admin=False
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def regular_token(self, regular_user):
        """JWT token for non-admin."""
        return create_access_token(
            user_id=str(regular_user.user_id),
            email=regular_user.email,
            account_type="verified"
        )

    def test_verify_requires_admin(self, client, regular_token):
        """Non-admin users cannot access verify endpoint."""
        response = client.get(
            "/api/v1/audit/verify",
            headers={"Authorization": f"Bearer {regular_token}"}
        )
        assert response.status_code == 403

    def test_verify_empty_chain_is_valid(self, client, admin_token):
        """Empty audit log returns valid chain with 0 entries verified."""
        response = client.get(
            "/api/v1/audit/verify",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["entries_verified"] == 0

    def test_verify_chain_with_entries(
        self, client, admin_token, db_session
    ):
        """Chain verification succeeds with valid audit entries."""
        audit_repo = AuditRepository(db_session)
        user_id = None  # System event

        for i in range(3):
            audit_repo.create_log(
                event_type=f"test.event.{i}",
                user_id=user_id,
                actor_id=user_id,
                resource_type="test",
                resource_id=f"resource-{i}",
                operation=AuditOperation.create,
                legal_basis="legitimate_interest"
            )

        response = client.get(
            "/api/v1/audit/verify",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        assert data["is_valid"] is True
        assert data["entries_verified"] == 3
