"""
Unit Tests for Soft Deletion and Account Restoration

Tests GDPR Article 17 soft deletion, account restoration flow,
permanent purge, and deletion status with mocked repositories.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID

from src.services.privacy_service import (
    PrivacyService,
    ProfileNotFoundError,
    AccountAlreadyDeletedError,
)
from src.services.auth_service import AuthService
from src.models.audit import AuditEventType, AuditOperation


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_profile_repo():
    return Mock()


@pytest.fixture
def mock_context_repo():
    return Mock()


@pytest.fixture
def mock_auth_repo():
    repo = Mock()
    repo.db = Mock()
    return repo


@pytest.fixture
def mock_oauth_repo():
    return Mock()


@pytest.fixture
def mock_audit_service():
    return Mock()


@pytest.fixture
def privacy_service(
    mock_profile_repo,
    mock_context_repo,
    mock_auth_repo,
    mock_oauth_repo,
    mock_audit_service,
):
    return PrivacyService(
        profile_repo=mock_profile_repo,
        context_repo=mock_context_repo,
        auth_repo=mock_auth_repo,
        oauth_repo=mock_oauth_repo,
        audit_service=mock_audit_service,
    )


@pytest.fixture
def auth_service(mock_auth_repo, mock_profile_repo, mock_audit_service):
    return AuthService(
        mock_auth_repo, mock_profile_repo, audit_service=mock_audit_service
    )


# ---------------------------------------------------------------------------
# Mock builders
# ---------------------------------------------------------------------------

def _make_profile(user_id):
    profile = Mock()
    profile.user_id = user_id
    profile.account_type = Mock(value="verified")
    profile.legal_name = "Test User"
    profile.primary_email = "test@example.com"
    return profile


def _make_auth_user(user_id, deleted_at=None, email="test@example.com"):
    auth = Mock()
    auth.user_id = user_id if isinstance(user_id, str) else str(user_id)
    auth.email = email
    auth.password_hash = "$argon2id$v=19$m=65536,t=3,p=4$FAKE"
    auth.is_email_verified = True
    auth.is_admin = False
    auth.created_at = datetime.now(timezone.utc)
    auth.deleted_at = deleted_at
    auth.is_locked = Mock(return_value=False)
    return auth


# ===================================================================
# Privacy Service: Soft Delete Account
# ===================================================================

class TestSoftDeleteAccount:
    """Tests for PrivacyService.soft_delete_account."""

    def test_soft_delete_sets_deleted_at_on_all_tables(
        self, privacy_service, mock_profile_repo, mock_auth_repo,
        mock_context_repo, mock_oauth_repo
    ):
        """Soft delete calls repository methods for auth, profile, and contexts."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        auth = _make_auth_user(user_id)
        mock_auth_repo.get_by_user_id.return_value = auth

        result = privacy_service.soft_delete_account(user_id=user_id)

        mock_auth_repo.soft_delete.assert_called_once_with(str(user_id))
        mock_profile_repo.soft_delete_profile.assert_called_once_with(user_id)
        mock_context_repo.soft_delete_user_contexts.assert_called_once_with(user_id)
        assert result["status"] == "scheduled"

    def test_soft_delete_raises_on_missing_profile(
        self, privacy_service, mock_profile_repo
    ):
        """ProfileNotFoundError raised when profile does not exist."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = None

        with pytest.raises(ProfileNotFoundError):
            privacy_service.soft_delete_account(user_id=user_id)

    def test_soft_delete_raises_on_missing_auth_user(
        self, privacy_service, mock_profile_repo, mock_auth_repo
    ):
        """ProfileNotFoundError raised when auth_user does not exist."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_auth_repo.get_by_user_id.return_value = None

        with pytest.raises(ProfileNotFoundError):
            privacy_service.soft_delete_account(user_id=user_id)

    def test_soft_delete_raises_on_already_deleted(
        self, privacy_service, mock_profile_repo, mock_auth_repo
    ):
        """AccountAlreadyDeletedError raised for already soft-deleted account."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        auth = _make_auth_user(user_id, deleted_at=datetime.now(timezone.utc))
        mock_auth_repo.get_by_user_id.return_value = auth

        with pytest.raises(AccountAlreadyDeletedError):
            privacy_service.soft_delete_account(user_id=user_id)

    def test_oauth_tokens_revoked_on_soft_delete(
        self, privacy_service, mock_profile_repo, mock_auth_repo,
        mock_oauth_repo
    ):
        """Soft delete revokes all OAuth access and refresh tokens."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)

        privacy_service.soft_delete_account(user_id=user_id)

        mock_oauth_repo.revoke_all_user_tokens.assert_called_once_with(user_id)
        mock_oauth_repo.revoke_all_user_refresh_tokens.assert_called_once_with(user_id)

    def test_consents_withdrawn_on_soft_delete(
        self, privacy_service, mock_profile_repo, mock_auth_repo,
        mock_oauth_repo
    ):
        """Soft delete withdraws all active OAuth consents."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)

        privacy_service.soft_delete_account(user_id=user_id)

        mock_oauth_repo.withdraw_all_user_consents.assert_called_once_with(user_id)

    def test_audit_log_created_for_deletion(
        self, privacy_service, mock_profile_repo, mock_auth_repo,
        mock_audit_service
    ):
        """Soft delete creates an audit event with correct type and legal basis."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)

        privacy_service.soft_delete_account(
            user_id=user_id,
            actor_id=user_id,
            ip_address="10.0.0.1",
            user_agent="TestAgent/1.0",
        )

        mock_audit_service.log_event.assert_called_once()
        call_kwargs = mock_audit_service.log_event.call_args[1]
        assert call_kwargs["event_type"] == AuditEventType.account_deletion_requested
        assert call_kwargs["operation"] == AuditOperation.delete
        assert call_kwargs["legal_basis"] == "gdpr_art_17_erasure"
        assert call_kwargs["user_id"] == user_id

    @patch("src.services.privacy_service.settings")
    def test_configurable_retention_days(
        self, mock_settings, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo, mock_audit_service
    ):
        """Retention period uses the configured DELETION_RETENTION_DAYS value."""
        mock_settings.DELETION_RETENTION_DAYS = 60
        service = PrivacyService(
            profile_repo=mock_profile_repo,
            context_repo=mock_context_repo,
            auth_repo=mock_auth_repo,
            oauth_repo=mock_oauth_repo,
            audit_service=mock_audit_service,
        )
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)

        result = service.soft_delete_account(user_id=user_id)

        # Permanent deletion date should be ~60 days out
        scheduled = datetime.fromisoformat(result["deletion_scheduled_at"])
        permanent = datetime.fromisoformat(result["permanent_deletion_date"])
        delta = (permanent - scheduled).days
        assert delta == 60

    def test_soft_delete_returns_scheduling_info(
        self, privacy_service, mock_profile_repo, mock_auth_repo
    ):
        """Return dict contains status, dates, and user-facing message."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)

        result = privacy_service.soft_delete_account(user_id=user_id)

        assert result["status"] == "scheduled"
        assert "deletion_scheduled_at" in result
        assert "permanent_deletion_date" in result
        assert "message" in result
        assert "30 days" in result["message"]


# ===================================================================
# Privacy Service: Deletion Status
# ===================================================================

class TestDeletionStatus:
    """Tests for PrivacyService.get_deletion_status."""

    def test_deletion_status_active(
        self, privacy_service, mock_auth_repo
    ):
        """Active (non-deleted) account returns status 'active'."""
        user_id = uuid4()
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)

        result = privacy_service.get_deletion_status(user_id=user_id)

        assert result["status"] == "active"

    def test_deletion_status_scheduled(
        self, privacy_service, mock_auth_repo
    ):
        """Soft-deleted account within grace period returns 'scheduled'."""
        user_id = uuid4()
        # get_by_user_id returns None (deleted_at filter)
        mock_auth_repo.get_by_user_id.return_value = None
        mock_auth_repo.get_by_email_including_deleted.return_value = None

        # Direct DB query returns the soft-deleted user
        deleted_at = datetime.now(timezone.utc) - timedelta(days=5)
        mock_result = Mock()
        mock_scalars = Mock()
        mock_user = _make_auth_user(user_id, deleted_at=deleted_at)
        mock_scalars.first.return_value = mock_user
        mock_result.scalars.return_value = mock_scalars
        mock_auth_repo.db.execute.return_value = mock_result

        result = privacy_service.get_deletion_status(user_id=user_id)

        assert result["status"] == "scheduled"
        assert "deletion_scheduled_at" in result
        assert "permanent_deletion_date" in result

    def test_deletion_status_purged(
        self, privacy_service, mock_auth_repo
    ):
        """Fully purged account (no record) returns 'purged'."""
        user_id = uuid4()
        mock_auth_repo.get_by_user_id.return_value = None
        mock_auth_repo.get_by_email_including_deleted.return_value = None

        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.first.return_value = None
        mock_result.scalars.return_value = mock_scalars
        mock_auth_repo.db.execute.return_value = mock_result

        result = privacy_service.get_deletion_status(user_id=user_id)

        assert result["status"] == "purged"


# ===================================================================
# Privacy Service: Purge Expired Accounts
# ===================================================================

class TestPurgeExpiredAccounts:
    """Tests for PrivacyService.purge_expired_accounts."""

    def test_permanent_purge_cascades(
        self, privacy_service, mock_auth_repo, mock_profile_repo,
        mock_audit_service
    ):
        """Hard delete is called on both auth_users and base_profiles."""
        user_id = uuid4()
        expired_user = _make_auth_user(
            user_id,
            deleted_at=datetime.now(timezone.utc) - timedelta(days=40),
        )
        mock_auth_repo.get_expired_soft_deleted_users.return_value = [expired_user]

        count = privacy_service.purge_expired_accounts(retention_days=30)

        assert count == 1
        mock_profile_repo.hard_delete_profile.assert_called_once_with(
            expired_user.user_id
        )
        mock_auth_repo.hard_delete.assert_called_once_with(str(expired_user.user_id))

    def test_audit_logs_preserved_after_purge(
        self, privacy_service, mock_auth_repo, mock_profile_repo,
        mock_audit_service
    ):
        """Purge audit event uses hashed ID (no PII) and sets user_id to None."""
        user_id = uuid4()
        expired_user = _make_auth_user(
            user_id,
            deleted_at=datetime.now(timezone.utc) - timedelta(days=40),
        )
        mock_auth_repo.get_expired_soft_deleted_users.return_value = [expired_user]

        privacy_service.purge_expired_accounts(retention_days=30)

        mock_audit_service.log_event.assert_called_once()
        call_kwargs = mock_audit_service.log_event.call_args[1]
        assert call_kwargs["event_type"] == AuditEventType.account_permanently_purged
        assert call_kwargs["user_id"] is None
        assert call_kwargs["actor_id"] is None
        assert call_kwargs["resource_id"].startswith("purged:")
        assert call_kwargs["legal_basis"] == "gdpr_art_17_retention_expiry"

    def test_purge_returns_zero_when_no_expired(
        self, privacy_service, mock_auth_repo
    ):
        """Returns 0 when no accounts have exceeded the grace period."""
        mock_auth_repo.get_expired_soft_deleted_users.return_value = []

        count = privacy_service.purge_expired_accounts(retention_days=30)

        assert count == 0

    @patch("src.services.privacy_service.settings")
    def test_purge_uses_config_default(
        self, mock_settings, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo, mock_audit_service
    ):
        """When retention_days is None, the config default is used."""
        mock_settings.DELETION_RETENTION_DAYS = 45
        service = PrivacyService(
            profile_repo=mock_profile_repo,
            context_repo=mock_context_repo,
            auth_repo=mock_auth_repo,
            oauth_repo=mock_oauth_repo,
            audit_service=mock_audit_service,
        )
        mock_auth_repo.get_expired_soft_deleted_users.return_value = []

        service.purge_expired_accounts()

        mock_auth_repo.get_expired_soft_deleted_users.assert_called_once_with(45)


# ===================================================================
# Auth Service: Login with Soft-Deleted Account
# ===================================================================

class TestLoginSoftDeleted:
    """Tests for login behavior when account is soft-deleted."""

    @pytest.fixture
    def mock_auth_repo(self):
        repo = Mock()
        repo.db = Mock()
        return repo

    @pytest.fixture
    def mock_profile_repo(self):
        return Mock()

    @pytest.fixture
    def auth_service(self, mock_auth_repo, mock_profile_repo):
        return AuthService(mock_auth_repo, mock_profile_repo)

    def test_soft_deleted_user_login_returns_account_deleted(
        self, auth_service, mock_auth_repo
    ):
        """Login for soft-deleted account within grace period returns ACCOUNT_DELETED."""
        mock_auth_repo.get_by_email.return_value = None
        deleted_user = _make_auth_user(
            "00000000-0000-0000-0000-000000000099",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        mock_auth_repo.get_by_email_including_deleted.return_value = deleted_user

        success, error, data = auth_service.login(
            email="test@example.com", password="AnyPass123!"
        )

        assert success is False
        assert error == "ACCOUNT_DELETED"
        assert data is not None
        assert "deletion_scheduled_at" in data
        assert "permanent_deletion_date" in data
        assert "recovery_info" in data

    def test_expired_soft_deleted_user_login_returns_invalid(
        self, auth_service, mock_auth_repo
    ):
        """Login for expired soft-deleted account returns generic invalid error."""
        mock_auth_repo.get_by_email.return_value = None
        deleted_user = _make_auth_user(
            "00000000-0000-0000-0000-000000000099",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=35),
        )
        mock_auth_repo.get_by_email_including_deleted.return_value = deleted_user

        success, error, data = auth_service.login(
            email="test@example.com", password="AnyPass123!"
        )

        assert success is False
        assert error == "Invalid email or password"
        assert data is None


# ===================================================================
# Auth Service: Registration with Recoverable Account
# ===================================================================

class TestRegisterRecoverable:
    """Tests for registration detecting a recoverable soft-deleted account."""

    @pytest.fixture
    def mock_auth_repo(self):
        return Mock()

    @pytest.fixture
    def mock_profile_repo(self):
        return Mock()

    @pytest.fixture
    def auth_service(self, mock_auth_repo, mock_profile_repo):
        return AuthService(mock_auth_repo, mock_profile_repo)

    @patch("src.services.auth_service.send_verification_email")
    def test_register_detects_recoverable_account_returns_409(
        self, mock_send_email, auth_service, mock_auth_repo
    ):
        """Registration with email of recoverable account returns ACCOUNT_RECOVERABLE."""
        mock_auth_repo.get_by_email.return_value = None
        deleted_user = _make_auth_user(
            "00000000-0000-0000-0000-000000000099",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        mock_auth_repo.get_by_email_including_deleted.return_value = deleted_user

        success, error, data = auth_service.register_user(
            email="test@example.com",
            password="SecurePass123!",
            user_id="00000000-0000-0000-0000-000000000200",
            display_name="Test User",
        )

        assert success is False
        assert error == "ACCOUNT_RECOVERABLE"
        assert data["account_recoverable"] is True
        assert "permanent_deletion_date" in data
        assert "restore_endpoint" in data

    @patch("src.services.auth_service.send_verification_email")
    def test_register_allows_new_account_after_grace_period(
        self, mock_send_email, auth_service, mock_auth_repo
    ):
        """Registration proceeds when the soft-deleted account has expired."""
        mock_auth_repo.get_by_email.return_value = None
        expired_user = _make_auth_user(
            "00000000-0000-0000-0000-000000000099",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=35),
        )
        mock_auth_repo.get_by_email_including_deleted.return_value = expired_user
        mock_auth_user = Mock()
        mock_auth_user.user_id = "00000000-0000-0000-0000-000000000200"
        mock_auth_user.email = "test@example.com"
        mock_auth_repo.create.return_value = mock_auth_user

        success, error, data = auth_service.register_user(
            email="test@example.com",
            password="SecurePass123!",
            user_id="00000000-0000-0000-0000-000000000200",
            display_name="Test User",
        )

        assert success is True
        assert error is None
        assert data["email"] == "test@example.com"
        mock_auth_repo.create.assert_called_once()


# ===================================================================
# Auth Service: Request Account Restoration
# ===================================================================

class TestRequestAccountRestoration:
    """Tests for AuthService.request_account_restoration."""

    @pytest.fixture
    def mock_auth_repo(self):
        return Mock()

    @pytest.fixture
    def mock_profile_repo(self):
        return Mock()

    @pytest.fixture
    def auth_service(self, mock_auth_repo, mock_profile_repo):
        return AuthService(mock_auth_repo, mock_profile_repo)

    @patch("src.services.auth_service.send_restoration_email")
    def test_restore_account_sends_email_returns_success(
        self, mock_send_email, auth_service, mock_auth_repo
    ):
        """Restoration request for recoverable account sends email and returns success."""
        deleted_user = _make_auth_user(
            "00000000-0000-0000-0000-000000000099",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        mock_auth_repo.get_by_email_including_deleted.return_value = deleted_user

        success, error = auth_service.request_account_restoration("test@example.com")

        assert success is True
        assert error is None
        mock_auth_repo.set_restoration_token.assert_called_once()
        mock_send_email.delay.assert_called_once()

    def test_restore_account_nonexistent_email_returns_success(
        self, auth_service, mock_auth_repo
    ):
        """Restoration request for unknown email returns success (enumeration prevention)."""
        mock_auth_repo.get_by_email_including_deleted.return_value = None

        success, error = auth_service.request_account_restoration("nobody@example.com")

        assert success is True
        assert error is None

    @patch("src.services.auth_service.send_restoration_email")
    def test_restore_account_expired_grace_returns_success_no_email(
        self, mock_send_email, auth_service, mock_auth_repo
    ):
        """Expired grace period returns success but does not send email."""
        expired_user = _make_auth_user(
            "00000000-0000-0000-0000-000000000099",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=35),
        )
        mock_auth_repo.get_by_email_including_deleted.return_value = expired_user

        success, error = auth_service.request_account_restoration("test@example.com")

        assert success is True
        mock_send_email.delay.assert_not_called()

    def test_restore_account_active_account_returns_success(
        self, auth_service, mock_auth_repo
    ):
        """Active (not deleted) account returns success without action."""
        active_user = _make_auth_user(
            "00000000-0000-0000-0000-000000000099", deleted_at=None
        )
        mock_auth_repo.get_by_email_including_deleted.return_value = active_user

        success, error = auth_service.request_account_restoration("test@example.com")

        assert success is True
        assert error is None


# ===================================================================
# Auth Service: Confirm Account Restoration
# ===================================================================

class TestConfirmAccountRestoration:
    """Tests for AuthService.confirm_account_restoration."""

    @pytest.fixture
    def mock_auth_repo(self):
        repo = Mock()
        repo.db = Mock()
        return repo

    @pytest.fixture
    def mock_profile_repo(self):
        return Mock()

    @pytest.fixture
    def mock_audit_service(self):
        return Mock()

    @pytest.fixture
    def auth_service(self, mock_auth_repo, mock_profile_repo, mock_audit_service):
        return AuthService(mock_auth_repo, mock_profile_repo, audit_service=mock_audit_service)

    def test_confirm_restoration_valid_token_restores_account(
        self, auth_service, mock_auth_repo, mock_profile_repo
    ):
        """Valid token and password restores account and returns JWT tokens."""
        user_id = "00000000-0000-0000-0000-000000000099"
        auth_user = _make_auth_user(
            user_id,
            deleted_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        auth_user.is_restoration_token_valid = Mock(return_value=True)
        mock_auth_repo.get_by_restoration_token.return_value = auth_user
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)

        # ContextRepository is created from mock_auth_repo.db inside the method
        success, error, data = auth_service.confirm_account_restoration(
            token="valid-token", new_password="NewSecurePass123!"
        )

        assert success is True
        assert error is None
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "restored_at" in data

        mock_auth_repo.restore_account.assert_called_once_with(user_id)
        mock_profile_repo.restore_profile.assert_called_once()
        mock_auth_repo.update_password.assert_called_once()
        mock_auth_repo.clear_restoration_token.assert_called_once()

    def test_confirm_restoration_invalid_token_returns_error(
        self, auth_service, mock_auth_repo
    ):
        """Invalid or unknown restoration token returns error."""
        mock_auth_repo.get_by_restoration_token.return_value = None

        success, error, data = auth_service.confirm_account_restoration(
            token="invalid-token", new_password="NewSecurePass123!"
        )

        assert success is False
        assert error == "INVALID_RESTORATION_TOKEN"
        assert data is None

    def test_confirm_restoration_expired_token_returns_error(
        self, auth_service, mock_auth_repo
    ):
        """Expired restoration token returns error."""
        auth_user = _make_auth_user(
            "00000000-0000-0000-0000-000000000099",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        auth_user.is_restoration_token_valid = Mock(return_value=False)
        mock_auth_repo.get_by_restoration_token.return_value = auth_user

        success, error, data = auth_service.confirm_account_restoration(
            token="expired-token", new_password="NewSecurePass123!"
        )

        assert success is False
        assert error == "INVALID_RESTORATION_TOKEN"
        assert data is None

    def test_confirm_restoration_expired_grace_period_returns_gone(
        self, auth_service, mock_auth_repo
    ):
        """Grace period expiry returns ACCOUNT_PERMANENTLY_DELETED."""
        auth_user = _make_auth_user(
            "00000000-0000-0000-0000-000000000099",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=35),
        )
        auth_user.is_restoration_token_valid = Mock(return_value=True)
        mock_auth_repo.get_by_restoration_token.return_value = auth_user

        success, error, data = auth_service.confirm_account_restoration(
            token="valid-token", new_password="NewSecurePass123!"
        )

        assert success is False
        assert error == "ACCOUNT_PERMANENTLY_DELETED"
        assert data is None

    def test_confirm_restoration_weak_password_returns_error(
        self, auth_service, mock_auth_repo
    ):
        """Weak new password fails validation."""
        auth_user = _make_auth_user(
            "00000000-0000-0000-0000-000000000099",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        auth_user.is_restoration_token_valid = Mock(return_value=True)
        mock_auth_repo.get_by_restoration_token.return_value = auth_user

        success, error, data = auth_service.confirm_account_restoration(
            token="valid-token", new_password="weak"
        )

        assert success is False
        assert "Password must" in error
        assert data is None

    def test_audit_log_created_for_restoration(
        self, auth_service, mock_auth_repo, mock_profile_repo,
        mock_audit_service
    ):
        """Account restoration creates an audit event."""
        user_id = "00000000-0000-0000-0000-000000000099"
        auth_user = _make_auth_user(
            user_id,
            deleted_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        auth_user.is_restoration_token_valid = Mock(return_value=True)
        mock_auth_repo.get_by_restoration_token.return_value = auth_user
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)

        auth_service.confirm_account_restoration(
            token="valid-token",
            new_password="NewSecurePass123!",
            ip_address="10.0.0.1",
            user_agent="TestAgent/1.0",
        )

        mock_audit_service.log_event.assert_called_once()
        call_kwargs = mock_audit_service.log_event.call_args[1]
        assert call_kwargs["event_type"] == AuditEventType.account_restored
        assert call_kwargs["operation"] == AuditOperation.restore
        assert call_kwargs["legal_basis"] == "contract"
