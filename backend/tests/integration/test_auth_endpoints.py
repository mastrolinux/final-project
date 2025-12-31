"""
Integration Tests for Authentication Endpoints

Tests complete HTTP request/response cycles for auth endpoints.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestRegisterEndpoint:
    """Test POST /api/v1/auth/register endpoint."""
    
    @patch('src.services.auth_service.send_verification_email')
    def test_register_success(self, mock_send_email, client):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "preferred_name": "New User"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["is_email_verified"] is False
        assert "user_id" in data
        assert "verify" in data["message"].lower()
        
        # Verify email task was queued
        mock_send_email.delay.assert_called_once()
    
    @patch('src.services.auth_service.send_verification_email')
    def test_register_duplicate_email(self, mock_send_email, client):
        """Test registration fails with duplicate email."""
        # Register first user
        client.post("/api/v1/auth/register", json={
            "email": "duplicate@example.com",
            "password": "SecurePass123!",
            "preferred_name": "First User"
        })
        
        # Try to register again with same email
        response = client.post("/api/v1/auth/register", json={
            "email": "duplicate@example.com",
            "password": "DifferentPass123!",
            "preferred_name": "Second User"
        })
        
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()
    
    def test_register_weak_password(self, client):
        """Test registration fails with weak password."""
        response = client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "password": "weak",
            "preferred_name": "Weak Password User"
        })
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_register_invalid_email(self, client):
        """Test registration fails with invalid email."""
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "SecurePass123!",
            "preferred_name": "Invalid Email User"
        })
        
        assert response.status_code == 422  # Pydantic validation error


class TestLoginEndpoint:
    """Test POST /api/v1/auth/login endpoint."""
    
    @patch('src.services.auth_service.send_verification_email')
    def test_login_success(self, mock_send_email, client):
        """Test successful login returns JWT tokens."""
        # Register user first
        client.post("/api/v1/auth/register", json={
            "email": "loginuser@example.com",
            "password": "SecurePass123!",
            "preferred_name": "Login User"
        })
        
        # Login
        response = client.post("/api/v1/auth/login", json={
            "email": "loginuser@example.com",
            "password": "SecurePass123!"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600
        assert data["email"] == "loginuser@example.com"
    
    def test_login_invalid_credentials(self, client):
        """Test login fails with invalid credentials."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "WrongPassword!"
        })
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    @patch('src.services.auth_service.send_verification_email')
    def test_login_wrong_password(self, mock_send_email, client):
        """Test login fails with wrong password."""
        # Register user
        client.post("/api/v1/auth/register", json={
            "email": "wrongpass@example.com",
            "password": "CorrectPass123!",
            "preferred_name": "Wrong Pass User"
        })
        
        # Login with wrong password
        response = client.post("/api/v1/auth/login", json={
            "email": "wrongpass@example.com",
            "password": "WrongPass123!"
        })
        
        assert response.status_code == 401


class TestVerifyEmailEndpoint:
    """Test POST /api/v1/auth/verify-email endpoint."""
    
    @patch('src.services.auth_service.send_verification_email')
    def test_verify_email_success(self, mock_send_email, client, db_session):
        """Test successful email verification."""
        # Register user
        response = client.post("/api/v1/auth/register", json={
            "email": "verify@example.com",
            "password": "SecurePass123!",
            "preferred_name": "Verify User"
        })
        user_id = response.json()["user_id"]
        
        # Get verification token from database
        from src.repositories.auth_repository import AuthRepository
        auth_repo = AuthRepository(db_session)
        auth_user = auth_repo.get_by_user_id(user_id)
        token = auth_user.verification_token
        
        # Verify email
        response = client.post("/api/v1/auth/verify-email", json={
            "token": token
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data["message"].lower()
    
    def test_verify_email_invalid_token(self, client):
        """Test email verification fails with invalid token."""
        response = client.post("/api/v1/auth/verify-email", json={
            "token": "invalid-token-that-does-not-exist-1234567890"
        })
        
        assert response.status_code == 400


class TestPasswordResetEndpoints:
    """Test password reset flow endpoints."""
    
    @patch('src.services.auth_service.send_password_reset_email')
    @patch('src.services.auth_service.send_verification_email')
    def test_password_reset_flow(self, mock_verify_email, mock_reset_email, client, db_session):
        """Test complete password reset flow."""
        # Register user
        response = client.post("/api/v1/auth/register", json={
            "email": "resetuser@example.com",
            "password": "OldPassword123!",
            "preferred_name": "Reset User"
        })
        assert response.status_code == 201
        
        # Request password reset
        response = client.post("/api/v1/auth/request-reset", json={
            "email": "resetuser@example.com"
        })
        assert response.status_code == 200
        assert "reset link" in response.json()["message"].lower()
        
        # Get reset token from database
        from src.repositories.auth_repository import AuthRepository
        auth_repo = AuthRepository(db_session)
        auth_user = auth_repo.get_by_email("resetuser@example.com")
        reset_token = auth_user.reset_token
        
        # Reset password with token
        response = client.post("/api/v1/auth/reset-password", json={
            "token": reset_token,
            "new_password": "NewPassword123!"
        })
        assert response.status_code == 200
        
        # Login with old password should fail
        response = client.post("/api/v1/auth/login", json={
            "email": "resetuser@example.com",
            "password": "OldPassword123!"
        })
        assert response.status_code == 401
        
        # Login with new password should succeed
        response = client.post("/api/v1/auth/login", json={
            "email": "resetuser@example.com",
            "password": "NewPassword123!"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    @patch('src.services.auth_service.send_password_reset_email')
    def test_request_reset_nonexistent_email(self, mock_send_email, client):
        """Test password reset request returns success for nonexistent email (security)."""
        response = client.post("/api/v1/auth/request-reset", json={
            "email": "doesnotexist@example.com"
        })
        
        # Should return success to prevent email enumeration
        assert response.status_code == 200
        
        # But email should not be sent
        mock_send_email.delay.assert_not_called()
    
    def test_reset_password_invalid_token(self, client):
        """Test password reset fails with invalid token."""
        response = client.post("/api/v1/auth/reset-password", json={
            "token": "invalid-reset-token-1234567890abcdef",
            "new_password": "NewPassword123!"
        })
        
        assert response.status_code == 400


class TestResendVerificationEndpoint:
    """Test POST /api/v1/auth/resend-verification endpoint."""
    
    @patch('src.services.auth_service.send_verification_email')
    def test_resend_verification_success(self, mock_send_email, client):
        """Test resending verification email."""
        # Register user (initial verification email sent)
        client.post("/api/v1/auth/register", json={
            "email": "resend@example.com",
            "password": "SecurePass123!",
            "preferred_name": "Resend User"
        })
        
        # Reset mock call count
        mock_send_email.delay.reset_mock()
        
        # Resend verification
        response = client.post("/api/v1/auth/resend-verification", json={
            "email": "resend@example.com"
        })
        
        assert response.status_code == 200
        assert "verification" in response.json()["message"].lower()
        
        # Verify new email was queued
        mock_send_email.delay.assert_called_once()
    
    def test_resend_verification_nonexistent_email(self, client):
        """Test resend fails for nonexistent email."""
        response = client.post("/api/v1/auth/resend-verification", json={
            "email": "doesnotexist@example.com"
        })

        assert response.status_code == 404


class TestRefreshEndpoint:
    """Test POST /api/v1/auth/refresh endpoint with token rotation."""

    @patch('src.api.v1.endpoints.auth.get_blacklist')
    @patch('src.services.auth_service.send_verification_email')
    def test_refresh_success(self, mock_send_email, mock_get_blacklist, client):
        """Test successful token refresh returns new tokens."""
        from unittest.mock import Mock

        # Setup mock blacklist
        mock_blacklist = Mock()
        mock_blacklist.is_blacklisted.return_value = False
        mock_blacklist.blacklist_token.return_value = None
        mock_get_blacklist.return_value = mock_blacklist

        # Register and login to get refresh token
        client.post("/api/v1/auth/register", json={
            "email": "refreshuser@example.com",
            "password": "SecurePass123!",
            "preferred_name": "Refresh User"
        })

        login_response = client.post("/api/v1/auth/login", json={
            "email": "refreshuser@example.com",
            "password": "SecurePass123!"
        })
        assert login_response.status_code == 200
        original_refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": original_refresh_token
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600

        # New tokens should be different from original
        assert data["refresh_token"] != original_refresh_token

    @patch('src.api.v1.endpoints.auth.get_blacklist')
    @patch('src.services.auth_service.send_verification_email')
    def test_refresh_returns_valid_access_token(self, mock_send_email, mock_get_blacklist, client):
        """Test refreshed access token is valid and contains correct claims."""
        from unittest.mock import Mock
        from src.core.security import verify_token
        import uuid

        # Setup mock blacklist
        mock_blacklist = Mock()
        mock_blacklist.is_blacklisted.return_value = False
        mock_blacklist.blacklist_token.return_value = None
        mock_get_blacklist.return_value = mock_blacklist

        # Use unique email to avoid conflicts
        unique_email = f"validtoken_{uuid.uuid4().hex[:8]}@example.com"

        # Register and login
        reg_response = client.post("/api/v1/auth/register", json={
            "email": unique_email,
            "password": "SecurePass123!",
            "preferred_name": "Valid Token User"
        })
        assert reg_response.status_code == 201, f"Registration failed: {reg_response.json()}"
        user_id = reg_response.json()["user_id"]

        login_response = client.post("/api/v1/auth/login", json={
            "email": unique_email,
            "password": "SecurePass123!"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.json()}"
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })

        assert response.status_code == 200
        new_access_token = response.json()["access_token"]

        # Verify new access token
        token_data = verify_token(new_access_token, token_type="access")
        assert token_data is not None
        assert token_data.user_id == user_id
        assert token_data.email == unique_email

    @patch('src.api.v1.endpoints.auth.get_blacklist')
    def test_refresh_fails_with_invalid_token(self, mock_get_blacklist, client):
        """Test refresh fails with malformed JWT token."""
        from unittest.mock import Mock

        mock_blacklist = Mock()
        mock_get_blacklist.return_value = mock_blacklist

        # Use a token that passes min_length validation but is invalid JWT
        # Needs to be at least 50 characters
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.invalid_signature_here"

        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": invalid_token
        })

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @patch('src.api.v1.endpoints.auth.get_blacklist')
    @patch('src.services.auth_service.send_verification_email')
    def test_refresh_fails_with_access_token(self, mock_send_email, mock_get_blacklist, client):
        """Test refresh fails when access token is provided instead of refresh token."""
        from unittest.mock import Mock

        mock_blacklist = Mock()
        mock_get_blacklist.return_value = mock_blacklist

        # Register and login
        client.post("/api/v1/auth/register", json={
            "email": "wrongtype@example.com",
            "password": "SecurePass123!",
            "preferred_name": "Wrong Type User"
        })

        login_response = client.post("/api/v1/auth/login", json={
            "email": "wrongtype@example.com",
            "password": "SecurePass123!"
        })
        access_token = login_response.json()["access_token"]

        # Try to refresh with access token instead of refresh token
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": access_token
        })

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @patch('src.api.v1.endpoints.auth.get_blacklist')
    @patch('src.services.auth_service.send_verification_email')
    def test_refresh_token_rotation_invalidates_old(self, mock_send_email, mock_get_blacklist, client):
        """Test that old refresh token is blacklisted after rotation."""
        from unittest.mock import Mock

        # Setup mock blacklist to track calls
        mock_blacklist = Mock()
        mock_blacklist.is_blacklisted.return_value = False
        mock_blacklist.blacklist_token.return_value = None
        mock_get_blacklist.return_value = mock_blacklist

        # Register and login
        client.post("/api/v1/auth/register", json={
            "email": "rotation@example.com",
            "password": "SecurePass123!",
            "preferred_name": "Rotation User"
        })

        login_response = client.post("/api/v1/auth/login", json={
            "email": "rotation@example.com",
            "password": "SecurePass123!"
        })
        original_refresh_token = login_response.json()["refresh_token"]

        # First refresh - should succeed
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": original_refresh_token
        })
        assert response.status_code == 200

        # Verify blacklist_token was called for the old token
        mock_blacklist.blacklist_token.assert_called_once()

        # Simulate old token being in blacklist now
        mock_blacklist.is_blacklisted.return_value = True

        # Try to use old refresh token again - should fail as revoked
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": original_refresh_token
        })
        assert response.status_code == 401

    @patch('src.api.v1.endpoints.auth.get_blacklist')
    @patch('src.services.auth_service.send_verification_email')
    def test_refresh_fails_with_revoked_token(self, mock_send_email, mock_get_blacklist, client):
        """Test refresh fails when token JTI is in blacklist (revoked)."""
        from unittest.mock import Mock

        # Setup mock blacklist to indicate token is revoked
        mock_blacklist = Mock()
        mock_blacklist.is_blacklisted.return_value = True
        mock_get_blacklist.return_value = mock_blacklist

        # Register and login
        client.post("/api/v1/auth/register", json={
            "email": "revoked@example.com",
            "password": "SecurePass123!",
            "preferred_name": "Revoked User"
        })

        login_response = client.post("/api/v1/auth/login", json={
            "email": "revoked@example.com",
            "password": "SecurePass123!"
        })
        refresh_token = login_response.json()["refresh_token"]

        # Try to refresh - should fail because token is blacklisted
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })

        assert response.status_code == 401

    @patch('src.api.v1.endpoints.auth.get_blacklist')
    def test_refresh_fails_when_redis_unavailable(self, mock_get_blacklist, client):
        """Test refresh returns 503 when Redis blacklist is unavailable."""

        # Simulate Redis being unavailable
        mock_get_blacklist.side_effect = RuntimeError("Redis is disabled")

        # Use a token that passes min_length validation (50+ chars)
        long_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.valid_looking_but_fake"

        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": long_token
        })

        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()

