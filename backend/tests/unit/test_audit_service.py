"""Tests for audit service: logging, error handling, and integrity verification."""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.services.audit_service import AuditService
from src.models.audit import AuditEventType, AuditOperation


@pytest.fixture
def mock_audit_repo():
    """Create a mock AuditRepository."""
    return Mock()


@pytest.fixture
def audit_service(mock_audit_repo):
    """Create AuditService with mock repository."""
    return AuditService(mock_audit_repo)


class TestLogEvent:
    """Test audit event logging."""

    def test_log_event_delegates_to_repository(self, audit_service, mock_audit_repo):
        """log_event calls repository.create_log with correct arguments."""
        user_id = uuid4()

        audit_service.log_event(
            event_type=AuditEventType.login_success,
            user_id=user_id,
            actor_id=user_id,
            resource_type="auth_user",
            resource_id=str(user_id),
            operation=AuditOperation.login,
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0",
            legal_basis="contract"
        )

        mock_audit_repo.create_log.assert_called_once_with(
            event_type="auth.login.success",
            user_id=user_id,
            actor_id=user_id,
            resource_type="auth_user",
            resource_id=str(user_id),
            operation=AuditOperation.login,
            changes=None,
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0",
            legal_basis="contract"
        )

    def test_log_event_with_changes(self, audit_service, mock_audit_repo):
        """log_event passes changes dict to repository."""
        user_id = uuid4()
        changes = {"email": "new@test.com"}

        audit_service.log_event(
            event_type=AuditEventType.profile_update,
            user_id=user_id,
            actor_id=user_id,
            resource_type="profile",
            resource_id=str(user_id),
            operation=AuditOperation.update,
            changes=changes
        )

        call_kwargs = mock_audit_repo.create_log.call_args
        assert call_kwargs[1]["changes"] == changes

    def test_log_event_swallows_exceptions(self, audit_service, mock_audit_repo):
        """log_event catches exceptions to avoid disrupting primary operations."""
        mock_audit_repo.create_log.side_effect = RuntimeError("DB connection lost")
        user_id = uuid4()

        # Should not raise
        audit_service.log_event(
            event_type=AuditEventType.login_success,
            user_id=user_id,
            actor_id=user_id,
            resource_type="auth_user",
            resource_id=str(user_id),
            operation=AuditOperation.login
        )

    def test_log_event_logs_exception(self, audit_service, mock_audit_repo, caplog):
        """log_event logs the exception when repository call fails."""
        mock_audit_repo.create_log.side_effect = RuntimeError("DB error")
        user_id = uuid4()

        with caplog.at_level(logging.ERROR):
            audit_service.log_event(
                event_type=AuditEventType.login_success,
                user_id=user_id,
                actor_id=user_id,
                resource_type="auth_user",
                resource_id=str(user_id),
                operation=AuditOperation.login
            )

        assert "Failed to record audit event" in caplog.text


class TestGetUserAuditTrail:
    """Test paginated audit trail retrieval."""

    def test_get_user_audit_trail_returns_paginated_dict(
        self, audit_service, mock_audit_repo
    ):
        """Returns dict with entries, total, limit, and offset."""
        user_id = uuid4()
        mock_entries = [Mock(), Mock()]
        mock_audit_repo.get_logs_for_user.return_value = mock_entries
        mock_audit_repo.count_logs_for_user.return_value = 2

        result = audit_service.get_user_audit_trail(user_id)

        assert result["entries"] == mock_entries
        assert result["total"] == 2
        assert result["limit"] == 50
        assert result["offset"] == 0

    def test_get_user_audit_trail_passes_filters(
        self, audit_service, mock_audit_repo
    ):
        """Passes event_type and resource_type filters to repository."""
        user_id = uuid4()
        mock_audit_repo.get_logs_for_user.return_value = []
        mock_audit_repo.count_logs_for_user.return_value = 0

        audit_service.get_user_audit_trail(
            user_id=user_id,
            event_type="auth.login.success",
            resource_type="auth_user",
            limit=10,
            offset=5
        )

        mock_audit_repo.get_logs_for_user.assert_called_once_with(
            user_id=user_id,
            event_type="auth.login.success",
            resource_type="auth_user",
            limit=10,
            offset=5
        )


class TestVerifyIntegrity:
    """Test hash chain integrity verification."""

    def test_verify_integrity_delegates_to_repository(
        self, audit_service, mock_audit_repo
    ):
        """verify_integrity calls repository.verify_chain."""
        mock_audit_repo.verify_chain.return_value = (True, 100, None)

        is_valid, count, error = audit_service.verify_integrity(limit=100)

        assert is_valid is True
        assert count == 100
        assert error is None
        mock_audit_repo.verify_chain.assert_called_once_with(limit=100)

    def test_verify_integrity_reports_failure(
        self, audit_service, mock_audit_repo
    ):
        """verify_integrity surfaces chain corruption detected by repository."""
        mock_audit_repo.verify_chain.return_value = (
            False, 50, "Hash mismatch at entry 42"
        )

        is_valid, count, error = audit_service.verify_integrity()

        assert is_valid is False
        assert count == 50
        assert "Hash mismatch" in error
