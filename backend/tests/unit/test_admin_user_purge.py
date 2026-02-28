"""Tests for admin user purge and soft-deleted user listing."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.services.privacy_service import PrivacyService


@pytest.fixture
def mock_profile_repo():
    return Mock()


@pytest.fixture
def mock_context_repo():
    return Mock()


@pytest.fixture
def mock_auth_repo():
    return Mock()


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


class TestListSoftDeletedUsers:
    """Tests for the list_soft_deleted_users service method."""

    def test_returns_users_and_count(self, privacy_service, mock_auth_repo):
        """Service returns soft-deleted users with total count."""
        user1 = Mock()
        user1.user_id = uuid4()
        user1.email = "deleted1@example.com"
        user1.deleted_at = datetime.now(UTC) - timedelta(days=5)

        user2 = Mock()
        user2.user_id = uuid4()
        user2.email = "deleted2@example.com"
        user2.deleted_at = datetime.now(UTC) - timedelta(days=10)

        mock_auth_repo.get_all_soft_deleted_users.return_value = [user1, user2]
        mock_auth_repo.count_soft_deleted_users.return_value = 2

        users, total = privacy_service.list_soft_deleted_users(offset=0, limit=20)

        assert len(users) == 2
        assert total == 2
        mock_auth_repo.get_all_soft_deleted_users.assert_called_once_with(offset=0, limit=20)
        mock_auth_repo.count_soft_deleted_users.assert_called_once()

    def test_returns_empty_when_no_deleted_users(self, privacy_service, mock_auth_repo):
        """Service returns empty list when no soft-deleted users exist."""
        mock_auth_repo.get_all_soft_deleted_users.return_value = []
        mock_auth_repo.count_soft_deleted_users.return_value = 0

        users, total = privacy_service.list_soft_deleted_users(offset=0, limit=20)

        assert len(users) == 0
        assert total == 0

    def test_pagination_parameters_forwarded(self, privacy_service, mock_auth_repo):
        """Service forwards offset and limit to the repository."""
        mock_auth_repo.get_all_soft_deleted_users.return_value = []
        mock_auth_repo.count_soft_deleted_users.return_value = 0

        privacy_service.list_soft_deleted_users(offset=40, limit=10)

        mock_auth_repo.get_all_soft_deleted_users.assert_called_once_with(offset=40, limit=10)


class TestPurgeExpiredAccounts:
    """Tests for the purge_expired_accounts service method."""

    def test_purges_expired_users(
        self,
        privacy_service,
        mock_auth_repo,
        mock_profile_repo,
        mock_audit_service,
    ):
        """Service purges users whose retention period has expired."""
        expired_user = Mock()
        expired_user.user_id = uuid4()
        expired_user.deleted_at = datetime.now(UTC) - timedelta(days=35)

        mock_auth_repo.get_expired_soft_deleted_users.return_value = [expired_user]
        mock_auth_repo.hard_delete.return_value = True
        mock_profile_repo.hard_delete_profile.return_value = True

        purged_count = privacy_service.purge_expired_accounts()

        assert purged_count == 1
        mock_profile_repo.hard_delete_profile.assert_called_once_with(expired_user.user_id)
        mock_auth_repo.hard_delete.assert_called_once_with(str(expired_user.user_id))

    def test_returns_zero_when_none_expired(self, privacy_service, mock_auth_repo):
        """Service returns 0 when no accounts have expired."""
        mock_auth_repo.get_expired_soft_deleted_users.return_value = []

        purged_count = privacy_service.purge_expired_accounts()

        assert purged_count == 0
        mock_auth_repo.hard_delete.assert_not_called()
