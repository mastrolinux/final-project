"""
Integration Tests for Audit Logging across Services

Verifies that audit log entries are created when performing operations
through the API: registration, login, profile updates, context creation,
and consent management.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.core.database import get_db
from src.core.security import create_access_token
from src.models.auth import AuthUser
from src.models.audit import AuditLog
from src.models.profile import BaseProfile, AccountType


class TestAuthAuditIntegration:
    """Verify audit logs created during authentication operations."""

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

    @patch('src.services.auth_service.send_verification_email')
    def test_registration_creates_audit_log(self, mock_email, client, db_session):
        """User registration produces an audit entry with event_type 'auth.register'."""
        response = client.post("/api/v1/auth/register", json={
            "email": "audit.reg@example.com",
            "password": "SecurePass123!",
            "preferred_name": "Audit User"
        })
        assert response.status_code == 201

        logs = db_session.query(AuditLog).filter(
            AuditLog.event_type == "auth.register"
        ).all()
        assert len(logs) >= 1

        log = logs[0]
        assert log.resource_type == "auth_user"
        assert log.operation.value == "register"
        assert log.legal_basis == "contract"
        # Hash chain fields populated
        assert log.entry_hash is not None
        assert log.previous_hash is not None
        assert len(log.entry_hash) == 64

    @patch('src.services.auth_service.send_verification_email')
    def test_login_success_creates_audit_log(
        self, mock_email, client, db_session
    ):
        """Successful login produces an audit entry with event_type 'auth.login.success'."""
        # Register user first
        client.post("/api/v1/auth/register", json={
            "email": "audit.login@example.com",
            "password": "SecurePass123!",
            "preferred_name": "Login User"
        })

        # Login
        response = client.post("/api/v1/auth/login", json={
            "email": "audit.login@example.com",
            "password": "SecurePass123!"
        })
        assert response.status_code == 200

        logs = db_session.query(AuditLog).filter(
            AuditLog.event_type == "auth.login.success"
        ).all()
        assert len(logs) >= 1
        assert logs[0].operation.value == "login"

    @patch('src.services.auth_service.send_verification_email')
    def test_login_failure_creates_audit_log(
        self, mock_email, client, db_session
    ):
        """Failed login produces an audit entry with event_type 'auth.login.failure'."""
        # Register user first
        client.post("/api/v1/auth/register", json={
            "email": "audit.fail@example.com",
            "password": "SecurePass123!",
            "preferred_name": "Fail User"
        })

        # Attempt login with wrong password
        response = client.post("/api/v1/auth/login", json={
            "email": "audit.fail@example.com",
            "password": "WrongPassword123!"
        })
        assert response.status_code == 401

        logs = db_session.query(AuditLog).filter(
            AuditLog.event_type == "auth.login.failure"
        ).all()
        assert len(logs) >= 1
        assert logs[0].changes == {"reason": "invalid_password"}


class TestProfileAuditIntegration:
    """Verify audit logs created during profile operations."""

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

    def test_create_profile_creates_audit_log(self, client, db_session):
        """Profile creation produces an audit entry with event_type 'profile.create'."""
        response = client.post("/api/v1/profiles", json={
            "account_type": "verified",
            "legal_name": "Audit Profile User",
            "primary_email": "audit.profile@example.com"
        })
        assert response.status_code == 201

        logs = db_session.query(AuditLog).filter(
            AuditLog.event_type == "profile.create"
        ).all()
        assert len(logs) >= 1
        assert logs[0].resource_type == "profile"
        assert logs[0].operation.value == "create"

    def test_update_profile_creates_audit_log(self, client, db_session):
        """Profile update produces an audit entry with event_type 'profile.update'."""
        # Create profile first
        create_resp = client.post("/api/v1/profiles", json={
            "account_type": "verified",
            "legal_name": "Update Test",
            "primary_email": "audit.update@example.com"
        })
        user_id = create_resp.json()["user_id"]

        # Update profile
        response = client.patch(f"/api/v1/profiles/{user_id}", json={
            "preferred_language": "fr"
        })
        assert response.status_code == 200

        logs = db_session.query(AuditLog).filter(
            AuditLog.event_type == "profile.update"
        ).all()
        assert len(logs) >= 1
        assert logs[0].operation.value == "update"

    def test_delete_profile_creates_audit_log(self, client, db_session):
        """Profile deletion produces an audit entry with event_type 'profile.delete'."""
        # Create profile first
        create_resp = client.post("/api/v1/profiles", json={
            "account_type": "unverified",
            "primary_email": "audit.delete@example.com"
        })
        user_id = create_resp.json()["user_id"]

        # Delete profile
        response = client.delete(f"/api/v1/profiles/{user_id}")
        assert response.status_code == 204

        logs = db_session.query(AuditLog).filter(
            AuditLog.event_type == "profile.delete"
        ).all()
        assert len(logs) >= 1
        assert logs[0].operation.value == "delete"


class TestAuditHashChainIntegrity:
    """Verify that audit entries form a valid hash chain."""

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

    @patch('src.services.auth_service.send_verification_email')
    def test_multiple_operations_maintain_hash_chain(
        self, mock_email, client, db_session
    ):
        """Multiple operations produce audit entries that form a valid hash chain."""
        from src.models.audit import GENESIS_HASH
        from src.repositories.audit_repository import AuditRepository

        # Create a series of auditable operations
        client.post("/api/v1/profiles", json={
            "account_type": "verified",
            "legal_name": "Chain Test User",
            "primary_email": "chain.test@example.com"
        })

        client.post("/api/v1/auth/register", json={
            "email": "chain.auth@example.com",
            "password": "SecurePass123!",
            "preferred_name": "Chain Auth"
        })

        # Verify chain integrity
        audit_repo = AuditRepository(db_session)
        is_valid, count, error = audit_repo.verify_chain(limit=100)

        assert is_valid is True
        assert count >= 2
        assert error is None

        # Verify first entry links to GENESIS_HASH
        first_entry = db_session.query(AuditLog).order_by(
            AuditLog.created_at.asc()
        ).first()
        assert first_entry.previous_hash == GENESIS_HASH
