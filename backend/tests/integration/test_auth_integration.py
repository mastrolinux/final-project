"""Integration tests for authentication workflows with mocked email."""

import secrets
from unittest.mock import patch

import pytest

from src.core.security import hash_password, verify_token
from src.models.profile import AccountType, BaseProfile
from src.repositories.auth_repository import AuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.services.auth_service import AuthService


class TestAuthIntegration:
    """Integration tests for authentication workflows."""

    @pytest.fixture
    def auth_repo(self, db_session):
        """Create auth repository with test database."""
        return AuthRepository(db_session)

    @pytest.fixture
    def profile_repo(self, db_session):
        """Create profile repository with test database."""
        return ProfileRepository(db_session)

    @pytest.fixture
    def auth_service(self, auth_repo, profile_repo):
        """Create auth service with real repositories."""
        return AuthService(auth_repo, profile_repo)

    @pytest.fixture
    def test_profile(self, db_session):
        """Create test base profile."""
        import uuid

        test_user_id = str(uuid.uuid4())
        profile = BaseProfile(
            user_id=test_user_id,
            account_type=AccountType.verified,
            primary_email="test@example.com",
            preferred_language="en",
        )
        db_session.add(profile)
        db_session.commit()
        return profile

    @patch("src.services.auth_service.send_verification_email")
    def test_register_and_verify_email_flow(self, mock_send_email, auth_service, test_profile):
        """Test complete registration and email verification flow."""
        success, error, data = auth_service.register_user(
            email="test@example.com",
            password="SecurePass123!",
            user_id=str(test_profile.user_id),
            display_name="Test User",
        )

        assert success is True
        assert data["is_email_verified"] is False

        mock_send_email.delay.assert_called_once()
        call_args = mock_send_email.delay.call_args[0]
        verification_token = call_args[1]

        success, error = auth_service.verify_email(verification_token)

        assert success is True
        assert error is None

    @patch("src.services.auth_service.send_verification_email")
    def test_login_after_registration(self, mock_send_email, auth_service, test_profile):
        """Test login after successful registration."""
        success, _, _ = auth_service.register_user(
            email="test@example.com",
            password="SecurePass123!",
            user_id=str(test_profile.user_id),
            display_name="Test User",
        )
        assert success is True

        success, error, data = auth_service.login(
            email="test@example.com", password="SecurePass123!"
        )

        assert success is True
        assert error is None
        assert "access_token" in data
        assert "refresh_token" in data

        access_token_data = verify_token(data["access_token"], token_type="access")
        assert access_token_data is not None
        assert access_token_data.user_id == str(test_profile.user_id)

        refresh_token_data = verify_token(data["refresh_token"], token_type="refresh")
        assert refresh_token_data is not None

    @patch("src.services.auth_service.send_password_reset_email")
    def test_password_reset_flow(self, mock_send_email, auth_service, auth_repo, test_profile):
        """Test complete password reset flow."""
        auth_user = auth_repo.create(
            email="test@example.com",
            password_hash=hash_password("OldPassword123!"),
            user_id=str(test_profile.user_id),
        )

        success, error = auth_service.request_password_reset("test@example.com")
        assert success is True

        mock_send_email.delay.assert_called_once()
        call_args = mock_send_email.delay.call_args[0]
        reset_token = call_args[1]

        success, error = auth_service.reset_password(reset_token, "NewPassword123!")
        assert success is True
        assert error is None

        success, _, _ = auth_service.login("test@example.com", "OldPassword123!")
        assert success is False

        success, _, data = auth_service.login("test@example.com", "NewPassword123!")
        assert success is True
        assert "access_token" in data

    def test_failed_login_locks_account(self, auth_service, auth_repo, test_profile):
        """Test account locks after 5 failed login attempts."""
        auth_user = auth_repo.create(
            email="test@example.com",
            password_hash=hash_password("CorrectPassword123!"),
            user_id=str(test_profile.user_id),
        )

        for i in range(5):
            success, error, _ = auth_service.login("test@example.com", "WrongPassword!")
            assert success is False

        success, error, _ = auth_service.login("test@example.com", "CorrectPassword123!")
        assert success is False
        assert "locked" in error.lower()

    @patch("src.services.auth_service.send_verification_email")
    def test_resend_verification_email(
        self, mock_send_email, auth_service, auth_repo, test_profile
    ):
        """Test resending verification email."""
        auth_user = auth_repo.create(
            email="test@example.com",
            password_hash=hash_password("Password123!"),
            user_id=str(test_profile.user_id),
        )

        success, error = auth_service.resend_verification_email("test@example.com")

        assert success is True
        assert error is None
        mock_send_email.delay.assert_called_once()

    def test_resend_verification_already_verified(self, auth_service, auth_repo, test_profile):
        """Test resend fails if email already verified."""
        auth_user = auth_repo.create(
            email="test@example.com",
            password_hash=hash_password("Password123!"),
            user_id=str(test_profile.user_id),
        )
        auth_repo.update_verification_status(str(test_profile.user_id), verified=True)

        success, error = auth_service.resend_verification_email("test@example.com")

        assert success is False
        assert "already verified" in error


class TestSetPasswordIntegration:
    """Integration tests for OAuth user setting a password."""

    @pytest.fixture
    def auth_repo(self, db_session):
        """Create auth repository with test database."""
        return AuthRepository(db_session)

    @pytest.fixture
    def profile_repo(self, db_session):
        """Create profile repository with test database."""
        return ProfileRepository(db_session)

    @pytest.fixture
    def auth_service(self, auth_repo, profile_repo):
        """Create auth service with real repositories."""
        return AuthService(auth_repo, profile_repo)

    @pytest.fixture
    def oauth_profile(self, db_session):
        """Create test base profile for OAuth user."""
        import uuid

        test_user_id = str(uuid.uuid4())
        profile = BaseProfile(
            user_id=test_user_id,
            account_type=AccountType.verified,
            primary_email="oauth@example.com",
            preferred_language="en",
        )
        db_session.add(profile)
        db_session.commit()
        return profile

    @pytest.fixture
    def oauth_user(self, auth_repo, oauth_profile):
        """Create an OAuth user with a random password hash (mimicking social auth registration)."""
        random_password_hash = hash_password(secrets.token_urlsafe(32))
        return auth_repo.create_user(
            email="oauth@example.com",
            password_hash=random_password_hash,
            user_id=str(oauth_profile.user_id),
            is_email_verified=True,
            provider="google",
            provider_id="google-sub-12345",
        )

    def test_set_password_full_flow(self, auth_service, auth_repo, oauth_user, oauth_profile):
        """Test full flow: OAuth user sets password, then logs in with email/password."""
        user_id = str(oauth_profile.user_id)

        success, error_code, data = auth_service.set_password(
            user_id=user_id, new_password="NewSecurePass123!"
        )

        assert success is True
        assert error_code is None
        assert data["email"] == "oauth@example.com"

        updated_user = auth_repo.get_by_user_id(user_id)
        assert updated_user.has_custom_password is True

        success, error, login_data = auth_service.login(
            email="oauth@example.com", password="NewSecurePass123!"
        )

        assert success is True
        assert "access_token" in login_data
        assert login_data["email"] == "oauth@example.com"

    def test_set_password_rejects_duplicate(self, auth_service, oauth_user, oauth_profile):
        """Test that password can only be set once via this method."""
        user_id = str(oauth_profile.user_id)

        success, _, _ = auth_service.set_password(user_id=user_id, new_password="FirstPass123!")
        assert success is True

        success, error_code, _ = auth_service.set_password(
            user_id=user_id, new_password="SecondPass123!"
        )
        assert success is False
        assert error_code == "PASSWORD_ALREADY_SET"

    def test_set_password_rejects_email_password_user(self, auth_service, auth_repo, db_session):
        """Test that email/password users cannot use set-password."""
        import uuid

        user_id = str(uuid.uuid4())
        profile = BaseProfile(
            user_id=user_id,
            account_type=AccountType.verified,
            primary_email="email@example.com",
            preferred_language="en",
        )
        db_session.add(profile)
        db_session.commit()

        auth_repo.create(
            email="email@example.com",
            password_hash=hash_password("ExistingPass123!"),
            user_id=user_id,
        )

        success, error_code, _ = auth_service.set_password(
            user_id=user_id, new_password="NewPass123!"
        )
        assert success is False
        assert error_code == "NOT_OAUTH_USER"

    @patch("src.services.auth_service.send_password_reset_email")
    def test_password_reset_works_after_set_password(
        self, mock_send_email, auth_service, auth_repo, oauth_user, oauth_profile
    ):
        """Test that password reset flow works for OAuth users who have set a password."""
        user_id = str(oauth_profile.user_id)

        success, _, _ = auth_service.set_password(user_id=user_id, new_password="InitialPass123!")
        assert success is True

        success, error = auth_service.request_password_reset("oauth@example.com")
        assert success is True

        mock_send_email.delay.assert_called_once()
        reset_token = mock_send_email.delay.call_args[0][1]

        success, error = auth_service.reset_password(reset_token, "ResetPass123!")
        assert success is True

        success, _, login_data = auth_service.login(
            email="oauth@example.com", password="ResetPass123!"
        )
        assert success is True
        assert "access_token" in login_data

    @patch("src.services.auth_service.send_password_reset_email")
    def test_password_reset_skipped_for_oauth_without_custom_password(
        self, mock_send_email, auth_service, oauth_user, oauth_profile
    ):
        """Test that password reset is silently skipped for OAuth users without custom password."""
        success, error = auth_service.request_password_reset("oauth@example.com")
        assert success is True
        mock_send_email.delay.assert_not_called()
