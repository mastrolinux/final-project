"""
Integration Tests for Authentication Workflows

Tests complete authentication flows with real database and mocked email sending.
"""

import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

from src.models.auth import AuthUser
from src.models.profile import BaseProfile, AccountType
from src.repositories.auth_repository import AuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.services.auth_service import AuthService
from src.core.security import hash_password, verify_token


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
            preferred_language="en"
        )
        db_session.add(profile)
        db_session.commit()
        return profile
    
    @patch('src.services.auth_service.send_verification_email')
    def test_register_and_verify_email_flow(self, mock_send_email, auth_service, test_profile):
        """Test complete registration and email verification flow."""
        # Step 1: Register user
        success, error, data = auth_service.register_user(
            email="test@example.com",
            password="SecurePass123!",
            user_id=str(test_profile.user_id),
            display_name="Test User"
        )
        
        assert success is True
        assert data["is_email_verified"] is False
        
        # Verify email was queued
        mock_send_email.delay.assert_called_once()
        call_args = mock_send_email.delay.call_args[0]
        verification_token = call_args[1]
        
        # Step 2: Verify email with token
        success, error = auth_service.verify_email(verification_token)
        
        assert success is True
        assert error is None
    
    @patch('src.services.auth_service.send_verification_email')
    def test_login_after_registration(self, mock_send_email, auth_service, test_profile):
        """Test login after successful registration."""
        # Step 1: Register
        success, _, _ = auth_service.register_user(
            email="test@example.com",
            password="SecurePass123!",
            user_id=str(test_profile.user_id),
            display_name="Test User"
        )
        assert success is True
        
        # Step 2: Login
        success, error, data = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        assert success is True
        assert error is None
        assert "access_token" in data
        assert "refresh_token" in data
        
        # Verify tokens are valid
        access_token_data = verify_token(data["access_token"], token_type="access")
        assert access_token_data is not None
        assert access_token_data.user_id == str(test_profile.user_id)
        
        refresh_token_data = verify_token(data["refresh_token"], token_type="refresh")
        assert refresh_token_data is not None
    
    @patch('src.services.auth_service.send_password_reset_email')
    def test_password_reset_flow(self, mock_send_email, auth_service, auth_repo, test_profile):
        """Test complete password reset flow."""
        # Setup: Create auth user with known password
        auth_user = auth_repo.create(
            email="test@example.com",
            password_hash=hash_password("OldPassword123!"),
            user_id=str(test_profile.user_id)
        )
        
        # Step 1: Request password reset
        success, error = auth_service.request_password_reset("test@example.com")
        assert success is True
        
        # Get reset token from mock call
        mock_send_email.delay.assert_called_once()
        call_args = mock_send_email.delay.call_args[0]
        reset_token = call_args[1]
        
        # Step 2: Reset password with token
        success, error = auth_service.reset_password(reset_token, "NewPassword123!")
        assert success is True
        assert error is None
        
        # Step 3: Verify old password no longer works
        success, _, _ = auth_service.login("test@example.com", "OldPassword123!")
        assert success is False
        
        # Step 4: Verify new password works
        success, _, data = auth_service.login("test@example.com", "NewPassword123!")
        assert success is True
        assert "access_token" in data
    
    def test_failed_login_locks_account(self, auth_service, auth_repo, test_profile):
        """Test account locks after 5 failed login attempts."""
        # Create auth user
        auth_user = auth_repo.create(
            email="test@example.com",
            password_hash=hash_password("CorrectPassword123!"),
            user_id=str(test_profile.user_id)
        )
        
        # Attempt 5 failed logins
        for i in range(5):
            success, error, _ = auth_service.login("test@example.com", "WrongPassword!")
            assert success is False
        
        # 6th attempt should be blocked due to lock
        success, error, _ = auth_service.login("test@example.com", "CorrectPassword123!")
        assert success is False
        assert "locked" in error.lower()
    
    @patch('src.services.auth_service.send_verification_email')
    def test_resend_verification_email(self, mock_send_email, auth_service, auth_repo, test_profile):
        """Test resending verification email."""
        # Create unverified auth user
        auth_user = auth_repo.create(
            email="test@example.com",
            password_hash=hash_password("Password123!"),
            user_id=str(test_profile.user_id)
        )
        
        # Resend verification
        success, error = auth_service.resend_verification_email("test@example.com")
        
        assert success is True
        assert error is None
        mock_send_email.delay.assert_called_once()
    
    def test_resend_verification_already_verified(self, auth_service, auth_repo, test_profile):
        """Test resend fails if email already verified."""
        # Create verified auth user
        auth_user = auth_repo.create(
            email="test@example.com",
            password_hash=hash_password("Password123!"),
            user_id=str(test_profile.user_id)
        )
        auth_repo.update_verification_status(str(test_profile.user_id), verified=True)
        
        # Try to resend
        success, error = auth_service.resend_verification_email("test@example.com")
        
        assert success is False
        assert "already verified" in error

