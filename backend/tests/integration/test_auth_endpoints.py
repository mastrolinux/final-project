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

