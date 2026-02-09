"""
Unit Tests for Audit Model and Enums

Tests AuditLog model creation, enum values, and hash chain constants.
"""

import pytest
from datetime import datetime, timezone

from src.models.audit import (
    AuditLog,
    AuditEventType,
    AuditOperation,
    GENESIS_HASH
)


class TestAuditOperation:
    """Test AuditOperation enum."""

    def test_operation_values(self):
        """Verify all operation enum values are lowercase strings."""
        expected = {
            "create", "update", "delete", "login", "logout",
            "register", "verify", "grant", "withdraw", "revoke",
            "restore"
        }
        actual = {op.value for op in AuditOperation}
        assert actual == expected

    def test_operation_is_string_enum(self):
        """AuditOperation members are usable as strings."""
        assert AuditOperation.create == "create"
        assert isinstance(AuditOperation.login, str)


class TestAuditEventType:
    """Test AuditEventType enum."""

    def test_auth_event_types(self):
        """Verify auth-related event type values follow dot-notation."""
        assert AuditEventType.login_success.value == "auth.login.success"
        assert AuditEventType.login_failure.value == "auth.login.failure"
        assert AuditEventType.register.value == "auth.register"
        assert AuditEventType.email_verification.value == "auth.email_verification"
        assert AuditEventType.password_reset.value == "auth.password_reset"
        assert AuditEventType.account_lock.value == "auth.account_lock"

    def test_profile_event_types(self):
        """Verify profile event type values."""
        assert AuditEventType.profile_create.value == "profile.create"
        assert AuditEventType.profile_update.value == "profile.update"
        assert AuditEventType.profile_delete.value == "profile.delete"

    def test_context_event_types(self):
        """Verify context event type values."""
        assert AuditEventType.context_create.value == "context.create"
        assert AuditEventType.context_update.value == "context.update"
        assert AuditEventType.context_delete.value == "context.delete"

    def test_consent_event_types(self):
        """Verify consent event type values."""
        assert AuditEventType.consent_grant.value == "consent.grant"
        assert AuditEventType.consent_withdraw.value == "consent.withdraw"

    def test_oauth_event_types(self):
        """Verify OAuth event type values."""
        assert AuditEventType.token_revoke.value == "oauth.token.revoke"
        assert AuditEventType.client_create.value == "oauth.client.create"
        assert AuditEventType.client_update.value == "oauth.client.update"
        assert AuditEventType.client_delete.value == "oauth.client.delete"
        assert AuditEventType.client_purge.value == "oauth.client.purge"

    def test_event_type_is_string_enum(self):
        """AuditEventType members are usable as strings."""
        assert isinstance(AuditEventType.login_success, str)


class TestGenesisHash:
    """Test GENESIS_HASH constant."""

    def test_genesis_hash_is_sha256(self):
        """GENESIS_HASH is a valid SHA-256 hex digest (64 chars)."""
        assert len(GENESIS_HASH) == 64
        assert all(c in "0123456789abcdef" for c in GENESIS_HASH)

    def test_genesis_hash_deterministic(self):
        """GENESIS_HASH matches SHA-256 of b'GENESIS'."""
        import hashlib
        expected = hashlib.sha256(b"GENESIS").hexdigest()
        assert GENESIS_HASH == expected


class TestAuditLogModel:
    """Test AuditLog SQLAlchemy model."""

    def test_model_tablename(self):
        """AuditLog uses 'audit_logs' table name."""
        assert AuditLog.__tablename__ == "audit_logs"

    def test_model_has_no_updated_at(self):
        """Immutable model has no updated_at column (by design)."""
        column_names = [c.name for c in AuditLog.__table__.columns]
        assert "updated_at" not in column_names

    def test_model_has_no_deleted_at(self):
        """Immutable model has no deleted_at column (by design)."""
        column_names = [c.name for c in AuditLog.__table__.columns]
        assert "deleted_at" not in column_names

    def test_model_has_required_columns(self):
        """AuditLog has all required columns for audit trail."""
        column_names = {c.name for c in AuditLog.__table__.columns}
        required = {
            "log_id", "created_at", "event_type", "user_id",
            "actor_id", "resource_type", "resource_id", "operation",
            "changes", "ip_address", "user_agent", "legal_basis",
            "previous_hash", "entry_hash"
        }
        assert required.issubset(column_names)

    def test_model_has_hash_chain_columns(self):
        """AuditLog has previous_hash and entry_hash for tamper evidence."""
        column_names = {c.name for c in AuditLog.__table__.columns}
        assert "previous_hash" in column_names
        assert "entry_hash" in column_names
