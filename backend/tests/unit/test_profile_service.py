"""
Unit Tests for ProfileService
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from src.services.profile_service import ProfileService, ProfileServiceError
from src.schemas.profile import ProfileCreate, ProfileUpdate, IdentityNameCreate
from src.models.profile import BaseProfile, IdentityName, AccountType, NameType


@pytest.fixture
def mock_repository():
    return Mock()


@pytest.fixture
def mock_auth_repository():
    return Mock()


@pytest.fixture
def profile_service(mock_repository):
    return ProfileService(mock_repository)


@pytest.fixture
def profile_service_with_auth(mock_repository, mock_auth_repository):
    return ProfileService(mock_repository, auth_repository=mock_auth_repository)


def test_create_verified_with_legal_name(profile_service, mock_repository):
    profile_data = ProfileCreate(
        account_type=AccountType.verified,
        legal_name="John Doe",
        primary_email="john@example.com"
    )
    
    mock_profile = BaseProfile(
        user_id=uuid4(),
        account_type=AccountType.verified,
        legal_name="John Doe",
        primary_email="john@example.com",
        preferred_language="en"
    )
    mock_repository.create_profile.return_value = mock_profile
    mock_repository.get_profile_by_email.return_value = None
    
    result = profile_service.create_profile(profile_data)
    
    assert result.account_type == AccountType.verified


def test_create_verified_without_legal_name_raises_error(profile_service, mock_repository):
    profile_data = ProfileCreate(
        account_type=AccountType.verified,
        legal_name=None,
        primary_email="john@example.com"
    )
    
    mock_repository.get_profile_by_email.return_value = None
    
    with pytest.raises(ProfileServiceError):
        profile_service.create_profile(profile_data)


def test_get_profile_existing(profile_service, mock_repository):
    user_id = uuid4()
    mock_profile = BaseProfile(
        user_id=user_id,
        primary_email="user@example.com",
        preferred_language="en"
    )
    mock_repository.get_profile_by_id.return_value = mock_profile
    
    result = profile_service.get_profile(user_id)
    
    assert result.user_id == user_id


def test_get_profile_nonexistent_raises_error(profile_service, mock_repository):
    mock_repository.get_profile_by_id.return_value = None
    
    with pytest.raises(ProfileServiceError):
        profile_service.get_profile(uuid4())


def test_delete_profile(profile_service, mock_repository):
    user_id = uuid4()
    mock_repository.soft_delete_profile.return_value = True

    result = profile_service.delete_profile(user_id)

    assert result is True


class TestEmailChangeReverification:
    """Tests for email change triggering re-verification."""

    def test_email_change_calls_auth_repo_update(
        self, profile_service_with_auth, mock_repository, mock_auth_repository
    ):
        """Changing email must sync auth_users and generate verification token."""
        user_id = uuid4()
        old_email = "old@example.com"
        new_email = "new@example.com"

        existing = BaseProfile(
            user_id=user_id,
            account_type=AccountType.unverified,
            legal_name="Test",
            primary_email=old_email,
            preferred_language="en",
        )
        mock_repository.get_profile_by_id.return_value = existing
        mock_repository.get_profile_by_email.return_value = None
        mock_repository.update_profile.return_value = existing
        mock_auth_repository.update_email.return_value = "test-token-abc"

        update = ProfileUpdate(primary_email=new_email)

        with patch("src.tasks.email_tasks.send_verification_email") as mock_send:
            mock_send.delay = Mock()
            profile_service_with_auth.update_profile(user_id, update)

        mock_auth_repository.update_email.assert_called_once_with(
            str(user_id), new_email
        )

    def test_email_change_dispatches_verification_email(
        self, profile_service_with_auth, mock_repository, mock_auth_repository
    ):
        """Changing email must dispatch a Celery verification email task."""
        user_id = uuid4()
        existing = BaseProfile(
            user_id=user_id,
            account_type=AccountType.unverified,
            legal_name="Alice",
            primary_email="old@example.com",
            preferred_language="en",
        )
        mock_repository.get_profile_by_id.return_value = existing
        mock_repository.get_profile_by_email.return_value = None
        mock_repository.update_profile.return_value = existing
        mock_auth_repository.update_email.return_value = "token-xyz"

        update = ProfileUpdate(primary_email="new@example.com")

        with patch(
            "src.tasks.email_tasks.send_verification_email"
        ) as mock_task:
            mock_task.delay = Mock()
            profile_service_with_auth.update_profile(user_id, update)
            mock_task.delay.assert_called_once_with(
                "new@example.com", "token-xyz", "Alice"
            )

    def test_email_change_sets_pending_flag(
        self, profile_service_with_auth, mock_repository, mock_auth_repository
    ):
        """Returned profile must carry email_verification_pending = True."""
        user_id = uuid4()
        existing = BaseProfile(
            user_id=user_id,
            account_type=AccountType.unverified,
            legal_name="Bob",
            primary_email="old@example.com",
            preferred_language="en",
        )
        mock_repository.get_profile_by_id.return_value = existing
        mock_repository.get_profile_by_email.return_value = None
        mock_repository.update_profile.return_value = existing
        mock_auth_repository.update_email.return_value = "tok"

        update = ProfileUpdate(primary_email="new@example.com")

        with patch("src.tasks.email_tasks.send_verification_email"):
            result = profile_service_with_auth.update_profile(user_id, update)

        assert getattr(result, "email_verification_pending", False) is True

    def test_same_email_no_reverification(
        self, profile_service_with_auth, mock_repository, mock_auth_repository
    ):
        """Updating with the same email must NOT trigger re-verification."""
        user_id = uuid4()
        same_email = "same@example.com"
        existing = BaseProfile(
            user_id=user_id,
            account_type=AccountType.unverified,
            primary_email=same_email,
            preferred_language="en",
        )
        mock_repository.get_profile_by_id.return_value = existing
        mock_repository.update_profile.return_value = existing

        update = ProfileUpdate(primary_email=same_email)
        profile_service_with_auth.update_profile(user_id, update)

        mock_auth_repository.update_email.assert_not_called()

    def test_no_auth_repo_no_reverification(
        self, profile_service, mock_repository
    ):
        """Without auth_repository injected, email change must not fail."""
        user_id = uuid4()
        existing = BaseProfile(
            user_id=user_id,
            account_type=AccountType.unverified,
            primary_email="old@example.com",
            preferred_language="en",
        )
        mock_repository.get_profile_by_id.return_value = existing
        mock_repository.get_profile_by_email.return_value = None
        mock_repository.update_profile.return_value = existing

        update = ProfileUpdate(primary_email="new@example.com")
        # Must not raise even without auth_repo
        result = profile_service.update_profile(user_id, update)
        assert result is not None
