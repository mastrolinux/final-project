"""Tests for audit repository: hash chain, log creation, and filtering."""

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.models.audit import GENESIS_HASH, AuditLog, AuditOperation
from src.repositories.audit_repository import AuditRepository


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    session = Mock()
    session.query.return_value = session
    session.filter.return_value = session
    session.order_by.return_value = session
    session.first.return_value = None
    return session


@pytest.fixture
def audit_repo(mock_db):
    """Create AuditRepository with mock session."""
    return AuditRepository(mock_db)


class TestHashComputation:
    """Test deterministic SHA-256 hash computation for chain integrity."""

    def test_compute_entry_hash_deterministic(self, audit_repo):
        """Same inputs produce the same hash."""
        ts = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        user_id = str(uuid4())

        hash1 = audit_repo._compute_entry_hash(
            timestamp=ts,
            event_type="auth.login.success",
            user_id=user_id,
            actor_id=user_id,
            resource_type="auth_user",
            resource_id=user_id,
            operation="login",
            changes=None,
            previous_hash=GENESIS_HASH,
        )

        hash2 = audit_repo._compute_entry_hash(
            timestamp=ts,
            event_type="auth.login.success",
            user_id=user_id,
            actor_id=user_id,
            resource_type="auth_user",
            resource_id=user_id,
            operation="login",
            changes=None,
            previous_hash=GENESIS_HASH,
        )

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_compute_entry_hash_different_inputs(self, audit_repo):
        """Different inputs produce different hashes."""
        ts = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        user_id = str(uuid4())

        hash1 = audit_repo._compute_entry_hash(
            timestamp=ts,
            event_type="auth.login.success",
            user_id=user_id,
            actor_id=user_id,
            resource_type="auth_user",
            resource_id=user_id,
            operation="login",
            changes=None,
            previous_hash=GENESIS_HASH,
        )

        hash2 = audit_repo._compute_entry_hash(
            timestamp=ts,
            event_type="auth.login.failure",
            user_id=user_id,
            actor_id=user_id,
            resource_type="auth_user",
            resource_id=user_id,
            operation="login",
            changes=None,
            previous_hash=GENESIS_HASH,
        )

        assert hash1 != hash2

    def test_compute_entry_hash_changes_sorted(self, audit_repo):
        """Changes dict is sorted for deterministic hashing."""
        ts = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        user_id = str(uuid4())

        hash1 = audit_repo._compute_entry_hash(
            timestamp=ts,
            event_type="profile.update",
            user_id=user_id,
            actor_id=user_id,
            resource_type="profile",
            resource_id=user_id,
            operation="update",
            changes={"email": "a@b.com", "name": "Alice"},
            previous_hash=GENESIS_HASH,
        )

        hash2 = audit_repo._compute_entry_hash(
            timestamp=ts,
            event_type="profile.update",
            user_id=user_id,
            actor_id=user_id,
            resource_type="profile",
            resource_id=user_id,
            operation="update",
            changes={"name": "Alice", "email": "a@b.com"},
            previous_hash=GENESIS_HASH,
        )

        assert hash1 == hash2

    def test_compute_entry_hash_none_user_id(self, audit_repo):
        """Hash computation handles None user_id (purged user)."""
        ts = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)

        result = audit_repo._compute_entry_hash(
            timestamp=ts,
            event_type="auth.login.success",
            user_id=None,
            actor_id=None,
            resource_type="auth_user",
            resource_id="some-id",
            operation="login",
            changes=None,
            previous_hash=GENESIS_HASH,
        )

        assert len(result) == 64

    def test_compute_entry_hash_is_sha256(self, audit_repo):
        """Hash output matches SHA-256 format."""
        ts = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        user_id = str(uuid4())

        result = audit_repo._compute_entry_hash(
            timestamp=ts,
            event_type="profile.create",
            user_id=user_id,
            actor_id=user_id,
            resource_type="profile",
            resource_id=user_id,
            operation="create",
            changes=None,
            previous_hash=GENESIS_HASH,
        )

        assert all(c in "0123456789abcdef" for c in result)


class TestGetLatestHash:
    """Test retrieval of latest hash for chain linking."""

    def test_returns_genesis_when_empty(self, audit_repo, mock_db):
        """Returns GENESIS_HASH when no entries exist."""
        mock_db.first.return_value = None
        result = audit_repo._get_latest_hash()
        assert result == GENESIS_HASH

    def test_returns_entry_hash_when_entries_exist(self, audit_repo, mock_db):
        """Returns the most recent entry_hash when entries exist."""
        expected_hash = "a" * 64
        mock_db.first.return_value = (expected_hash,)
        result = audit_repo._get_latest_hash()
        assert result == expected_hash


class TestCreateLog:
    """Test audit log entry creation."""

    def test_create_log_adds_to_session(self, audit_repo, mock_db):
        """create_log adds an AuditLog instance to the session and commits."""
        user_id = uuid4()

        audit_repo.create_log(
            event_type="auth.login.success",
            user_id=user_id,
            actor_id=user_id,
            resource_type="auth_user",
            resource_id=str(user_id),
            operation=AuditOperation.login,
            legal_basis="contract",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        added_obj = mock_db.add.call_args[0][0]
        assert isinstance(added_obj, AuditLog)
        assert added_obj.event_type == "auth.login.success"
        assert added_obj.user_id == user_id
        assert added_obj.resource_type == "auth_user"
        assert added_obj.operation == AuditOperation.login
        assert added_obj.previous_hash == GENESIS_HASH
        assert len(added_obj.entry_hash) == 64

    def test_create_log_with_changes(self, audit_repo, mock_db):
        """create_log persists changes dict as JSONB."""
        user_id = uuid4()
        changes = {"email": "new@test.com"}

        audit_repo.create_log(
            event_type="profile.update",
            user_id=user_id,
            actor_id=user_id,
            resource_type="profile",
            resource_id=str(user_id),
            operation=AuditOperation.update,
            changes=changes,
            legal_basis="contract",
        )

        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.changes == changes

    def test_create_log_with_ip_and_user_agent(self, audit_repo, mock_db):
        """create_log persists IP address and user agent."""
        user_id = uuid4()

        audit_repo.create_log(
            event_type="auth.login.success",
            user_id=user_id,
            actor_id=user_id,
            resource_type="auth_user",
            resource_id=str(user_id),
            operation=AuditOperation.login,
            ip_address="192.168.1.1",
            user_agent="TestBrowser/1.0",
        )

        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.ip_address == "192.168.1.1"
        assert added_obj.user_agent == "TestBrowser/1.0"
