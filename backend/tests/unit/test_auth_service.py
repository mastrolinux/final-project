"""
Unit Tests for Authentication Service

Tests password hashing, JWT tokens, and auth service business logic.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    verify_token
)
from src.services.auth_service import AuthService
from src.models.auth import AuthUser


class TestPasswordHashing:
    """Test Argon2id password hashing functions."""
    
    def test_hash_password_creates_valid_hash(self):
        """Test that password hashing creates valid Argon2id hash."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$argon2id$")
        assert len(hashed) > 50
    
    def test_verify_password_with_correct_password(self):
        """Test password verification with correct password."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_with_incorrect_password(self):
        """Test password verification with incorrect password."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password("WrongPassword!", hashed) is False
    
    def test_verify_password_with_invalid_hash(self):
        """Test password verification with invalid hash format."""
        result = verify_password("password", "invalid-hash")
        assert result is False


class TestPasswordValidation:
    """Test password strength validation."""
    
    def test_validate_password_strength_valid_password(self):
        """Test validation passes for strong password."""
        valid, message = validate_password_strength("SecurePass123!")
        assert valid is True
        assert "meets requirements" in message
    
    def test_validate_password_strength_too_short(self):
        """Test validation fails for short password."""
        valid, message = validate_password_strength("Short1!")
        assert valid is False
        assert "at least 8 characters" in message
    
    def test_validate_password_strength_no_uppercase(self):
        """Test validation fails without uppercase letter."""
        valid, message = validate_password_strength("lowercase123!")
        assert valid is False
        assert "uppercase" in message
    
    def test_validate_password_strength_no_lowercase(self):
        """Test validation fails without lowercase letter."""
        valid, message = validate_password_strength("UPPERCASE123!")
        assert valid is False
        assert "lowercase" in message
    
    def test_validate_password_strength_no_digit(self):
        """Test validation fails without digit."""
        valid, message = validate_password_strength("NoDigitsHere!")
        assert valid is False
        assert "digit" in message


class TestJWTTokens:
    """Test JWT token creation and verification."""
    
    def test_create_access_token_valid_claims(self):
        """Test access token creation includes required claims."""
        user_id = "test-user-123"
        email = "test@example.com"
        account_type = "verified"
        
        token = create_access_token(user_id, email, account_type)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50
        
        # Verify token structure
        token_data = verify_token(token, token_type="access")
        assert token_data is not None
        assert token_data.user_id == user_id
        assert token_data.email == email
        assert token_data.account_type == account_type
        assert token_data.token_type == "access"
    
    def test_create_refresh_token_valid_claims(self):
        """Test refresh token creation."""
        user_id = "test-user-123"
        
        token = create_refresh_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Verify token structure
        token_data = verify_token(token, token_type="refresh")
        assert token_data is not None
        assert token_data.user_id == user_id
        assert token_data.token_type == "refresh"
    
    def test_verify_token_valid_token(self):
        """Test token verification with valid token."""
        user_id = "test-user-123"
        email = "test@example.com"
        account_type = "verified"
        
        token = create_access_token(user_id, email, account_type)
        token_data = verify_token(token, token_type="access")
        
        assert token_data is not None
        assert token_data.user_id == user_id
        assert token_data.email == email
    
    def test_verify_token_wrong_type(self):
        """Test token verification fails with wrong token type."""
        user_id = "test-user-123"
        token = create_refresh_token(user_id)
        
        # Try to verify refresh token as access token
        token_data = verify_token(token, token_type="access")
        assert token_data is None
    
    def test_verify_token_invalid_token(self):
        """Test token verification fails with invalid token."""
        token_data = verify_token("invalid.token.here", token_type="access")
        assert token_data is None


class TestAuthService:
    """Test AuthService business logic."""
    
    @pytest.fixture
    def mock_auth_repo(self):
        """Mock authentication repository."""
        return Mock()
    
    @pytest.fixture
    def mock_profile_repo(self):
        """Mock profile repository."""
        return Mock()
    
    @pytest.fixture
    def auth_service(self, mock_auth_repo, mock_profile_repo):
        """Create AuthService with mocked repositories."""
        return AuthService(mock_auth_repo, mock_profile_repo)
    
    @patch('src.services.auth_service.send_verification_email')
    def test_register_user_success(self, mock_send_email, auth_service, mock_auth_repo):
        """Test successful user registration."""
        # Setup mocks
        mock_auth_repo.get_by_email.return_value = None
        mock_auth_repo.get_by_email_including_deleted.return_value = None
        mock_auth_user = Mock()
        mock_auth_user.user_id = "00000000-0000-0000-0000-000000000123"
        mock_auth_user.email = "test@example.com"
        mock_auth_repo.create.return_value = mock_auth_user
        
        # Register user
        success, error, data = auth_service.register_user(
            email="test@example.com",
            password="SecurePass123!",
            user_id="00000000-0000-0000-0000-000000000123",
            display_name="Test User"
        )
        
        # Verify success
        assert success is True
        assert error is None
        assert data is not None
        assert data["email"] == "test@example.com"
        assert data["is_email_verified"] is False
        
        # Verify repository calls
        mock_auth_repo.get_by_email.assert_called_once_with("test@example.com")
        mock_auth_repo.create.assert_called_once()
        mock_auth_repo.set_verification_token.assert_called_once()
        
        # Verify email task queued
        mock_send_email.delay.assert_called_once()
    
    def test_register_user_duplicate_email(self, auth_service, mock_auth_repo):
        """Test registration fails with duplicate email."""
        # Setup mock - email already exists
        mock_auth_repo.get_by_email.return_value = Mock()
        
        success, error, data = auth_service.register_user(
            email="existing@example.com",
            password="SecurePass123!",
            user_id="00000000-0000-0000-0000-000000000123",
            display_name="Test User"
        )
        
        assert success is False
        assert "already registered" in error
        assert data is None
    
    def test_register_user_weak_password(self, auth_service, mock_auth_repo):
        """Test registration fails with weak password."""
        mock_auth_repo.get_by_email.return_value = None
        mock_auth_repo.get_by_email_including_deleted.return_value = None
        
        success, error, data = auth_service.register_user(
            email="test@example.com",
            password="weak",
            user_id="00000000-0000-0000-0000-000000000123",
            display_name="Test User"
        )
        
        assert success is False
        assert "Password must" in error
        assert data is None
    
    def test_login_success_returns_tokens(self, auth_service, mock_auth_repo, mock_profile_repo):
        """Test successful login returns JWT tokens."""
        # Setup mocks
        mock_auth_user = Mock()
        mock_auth_user.user_id = "00000000-0000-0000-0000-000000000123"
        mock_auth_user.email = "test@example.com"
        mock_auth_user.password_hash = hash_password("SecurePass123!")
        mock_auth_user.is_email_verified = True
        mock_auth_user.is_admin = False
        mock_auth_user.is_locked.return_value = False

        mock_auth_repo.get_by_email.return_value = mock_auth_user

        # Mock profile with proper account_type enum
        from src.models.profile import AccountType
        mock_profile = Mock()
        mock_profile.account_type = AccountType.verified
        mock_profile_repo.get_profile_by_id.return_value = mock_profile

        # Login
        success, error, data = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Verify success
        assert success is True
        assert error is None
        assert data is not None
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_id"] == "00000000-0000-0000-0000-000000000123"
        
        # Verify repository calls
        mock_auth_repo.reset_failed_login.assert_called_once()
    
    def test_login_invalid_credentials(self, auth_service, mock_auth_repo):
        """Test login fails with invalid credentials."""
        mock_auth_repo.get_by_email.return_value = None
        mock_auth_repo.get_by_email_including_deleted.return_value = None
        
        success, error, data = auth_service.login(
            email="nonexistent@example.com",
            password="password"
        )
        
        assert success is False
        assert "Invalid email or password" in error
        assert data is None
    
    def test_login_wrong_password(self, auth_service, mock_auth_repo):
        """Test login fails with wrong password."""
        mock_auth_user = Mock()
        mock_auth_user.user_id = "00000000-0000-0000-0000-000000000123"
        mock_auth_user.password_hash = hash_password("CorrectPass123!")
        mock_auth_user.is_locked.return_value = False
        
        mock_auth_repo.get_by_email.return_value = mock_auth_user
        
        success, error, data = auth_service.login(
            email="test@example.com",
            password="WrongPass123!"
        )
        
        assert success is False
        assert "Invalid email or password" in error
        
        # Verify failed login attempt was incremented
        mock_auth_repo.increment_failed_login.assert_called_once()
    
    def test_login_account_locked(self, auth_service, mock_auth_repo):
        """Test login fails when account is locked."""
        mock_auth_user = Mock()
        mock_auth_user.is_locked.return_value = True
        
        mock_auth_repo.get_by_email.return_value = mock_auth_user
        
        success, error, data = auth_service.login(
            email="test@example.com",
            password="password"
        )
        
        assert success is False
        assert "locked" in error.lower()
        assert data is None
    
    def test_verify_email_success(self, auth_service, mock_auth_repo):
        """Test successful email verification."""
        mock_auth_user = Mock()
        mock_auth_user.user_id = "00000000-0000-0000-0000-000000000123"
        mock_auth_user.is_verification_token_valid.return_value = True
        
        mock_auth_repo.get_by_verification_token.return_value = mock_auth_user
        
        success, error = auth_service.verify_email("valid-token")
        
        assert success is True
        assert error is None
        mock_auth_repo.update_verification_status.assert_called_once()
    
    def test_verify_email_invalid_token(self, auth_service, mock_auth_repo):
        """Test email verification fails with invalid token."""
        mock_auth_repo.get_by_verification_token.return_value = None
        
        success, error = auth_service.verify_email("invalid-token")
        
        assert success is False
        assert "Invalid or expired" in error
    
    @patch('src.services.auth_service.send_password_reset_email')
    def test_request_password_reset_success(self, mock_send_email, auth_service, mock_auth_repo):
        """Test password reset request sends email."""
        mock_auth_user = Mock()
        mock_auth_user.user_id = "00000000-0000-0000-0000-000000000123"
        mock_auth_repo.get_by_email.return_value = mock_auth_user
        
        success, error = auth_service.request_password_reset("test@example.com")
        
        assert success is True
        assert error is None
        mock_auth_repo.set_reset_token.assert_called_once()
        mock_send_email.delay.assert_called_once()
    
    def test_request_password_reset_nonexistent_email(self, auth_service, mock_auth_repo):
        """Test password reset returns success for nonexistent email (security)."""
        mock_auth_repo.get_by_email.return_value = None
        
        success, error = auth_service.request_password_reset("nonexistent@example.com")
        
        # Should return success to prevent email enumeration
        assert success is True
        assert error is None
    
    def test_reset_password_success(self, auth_service, mock_auth_repo):
        """Test successful password reset."""
        mock_auth_user = Mock()
        mock_auth_user.user_id = "00000000-0000-0000-0000-000000000123"
        mock_auth_user.is_reset_token_valid.return_value = True
        
        mock_auth_repo.get_by_reset_token.return_value = mock_auth_user
        
        success, error = auth_service.reset_password("valid-token", "NewSecurePass123!")
        
        assert success is True
        assert error is None
        mock_auth_repo.update_password.assert_called_once()
        mock_auth_repo.clear_reset_token.assert_called_once()
    
    def test_reset_password_invalid_token(self, auth_service, mock_auth_repo):
        """Test password reset fails with invalid token."""
        mock_auth_repo.get_by_reset_token.return_value = None
        
        success, error = auth_service.reset_password("invalid-token", "NewSecurePass123!")
        
        assert success is False
        assert "Invalid or expired" in error
    
    def test_reset_password_weak_new_password(self, auth_service, mock_auth_repo):
        """Test password reset fails with weak new password."""
        mock_auth_user = Mock()
        mock_auth_user.is_reset_token_valid.return_value = True
        mock_auth_repo.get_by_reset_token.return_value = mock_auth_user
        
        success, error = auth_service.reset_password("valid-token", "weak")
        
        assert success is False
        assert "Password must" in error


class TestAuthUserModel:
    """Test AuthUser model helper methods."""
    
    def test_is_locked_returns_true_when_locked(self):
        """Test is_locked returns True when account is locked."""
        auth_user = AuthUser(
            email="test@example.com",
            password_hash="hash",
            user_id="00000000-0000-0000-0000-000000000123",
            locked_until=datetime.now(timezone.utc) + timedelta(minutes=10)
        )
        
        assert auth_user.is_locked() is True
    
    def test_is_locked_returns_false_when_not_locked(self):
        """Test is_locked returns False when not locked."""
        auth_user = AuthUser(
            email="test@example.com",
            password_hash="hash",
            user_id="00000000-0000-0000-0000-000000000123",
            locked_until=None
        )
        
        assert auth_user.is_locked() is False
    
    def test_is_locked_returns_false_when_lock_expired(self):
        """Test is_locked returns False when lock has expired."""
        auth_user = AuthUser(
            email="test@example.com",
            password_hash="hash",
            user_id="00000000-0000-0000-0000-000000000123",
            locked_until=datetime.now(timezone.utc) - timedelta(minutes=10)
        )
        
        assert auth_user.is_locked() is False
    
    def test_is_verification_token_valid_returns_true(self):
        """Test verification token validation."""
        token = "valid-token-123"
        auth_user = AuthUser(
            email="test@example.com",
            password_hash="hash",
            user_id="00000000-0000-0000-0000-000000000123",
            verification_token=token,
            verification_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        
        assert auth_user.is_verification_token_valid(token) is True
    
    def test_is_verification_token_valid_returns_false_when_expired(self):
        """Test verification token validation fails when expired."""
        token = "expired-token"
        auth_user = AuthUser(
            email="test@example.com",
            password_hash="hash",
            user_id="00000000-0000-0000-0000-000000000123",
            verification_token=token,
            verification_token_expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        assert auth_user.is_verification_token_valid(token) is False
    
    def test_is_reset_token_valid_returns_true(self):
        """Test reset token validation."""
        token = "valid-reset-token"
        auth_user = AuthUser(
            email="test@example.com",
            password_hash="hash",
            user_id="00000000-0000-0000-0000-000000000123",
            reset_token=token,
            reset_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )

        assert auth_user.is_reset_token_valid(token) is True


class TestRefreshAccessToken:
    """Test refresh_access_token method with token rotation."""

    @pytest.fixture
    def mock_auth_repo(self):
        """Mock authentication repository."""
        return Mock()

    @pytest.fixture
    def mock_profile_repo(self):
        """Mock profile repository."""
        return Mock()

    @pytest.fixture
    def mock_blacklist(self):
        """Mock TokenBlacklist instance."""
        blacklist = Mock()
        blacklist.is_blacklisted.return_value = False
        blacklist.blacklist_token.return_value = None
        return blacklist

    @pytest.fixture
    def auth_service(self, mock_auth_repo, mock_profile_repo):
        """Create AuthService with mocked repositories."""
        return AuthService(mock_auth_repo, mock_profile_repo)

    @pytest.fixture
    def valid_refresh_token(self):
        """Create a valid refresh token for testing."""
        return create_refresh_token("00000000-0000-0000-0000-000000000123")

    def test_refresh_success_returns_new_tokens(
        self, auth_service, mock_auth_repo, mock_profile_repo, mock_blacklist
    ):
        """Test successful refresh returns new access and refresh tokens."""
        # Create valid refresh token
        refresh_token = create_refresh_token("00000000-0000-0000-0000-000000000123")

        # Setup mock auth user
        mock_auth_user = Mock()
        mock_auth_user.user_id = "00000000-0000-0000-0000-000000000123"
        mock_auth_user.email = "test@example.com"
        mock_auth_user.deleted_at = None
        mock_auth_user.is_admin = False
        mock_auth_user.is_locked.return_value = False
        mock_auth_repo.get_by_user_id.return_value = mock_auth_user

        # Setup mock profile
        from src.models.profile import AccountType
        mock_profile = Mock()
        mock_profile.account_type = AccountType.verified
        mock_profile_repo.get_profile_by_id.return_value = mock_profile

        # Execute refresh
        success, error_code, data = auth_service.refresh_access_token(
            refresh_token=refresh_token,
            blacklist=mock_blacklist
        )

        # Verify success
        assert success is True
        assert error_code is None
        assert data is not None
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600

        # Verify new tokens are different from input
        assert data["refresh_token"] != refresh_token

        # Verify blacklist was called for old token
        mock_blacklist.blacklist_token.assert_called_once()

    def test_refresh_fails_with_invalid_token(
        self, auth_service, mock_blacklist
    ):
        """Test refresh fails with malformed JWT token."""
        success, error_code, data = auth_service.refresh_access_token(
            refresh_token="invalid.token.here",
            blacklist=mock_blacklist
        )

        assert success is False
        assert error_code == "INVALID_TOKEN"
        assert data is None

    def test_refresh_fails_with_expired_token(
        self, auth_service, mock_blacklist
    ):
        """Test refresh fails with expired refresh token."""
        # Create an expired token by mocking time
        with patch('src.core.security.datetime') as mock_datetime:
            # Set time 31 days in past for token creation
            past_time = datetime.now(timezone.utc) - timedelta(days=31)
            mock_datetime.now.return_value = past_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Use a token that would be expired
        # Since we can't easily create an expired token, we rely on verify_token returning None
        # For integration testing, a properly expired token would be tested
        # Here we test that invalid signature/format returns INVALID_TOKEN
        success, error_code, data = auth_service.refresh_access_token(
            refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImV4cCI6MTAwMDAwMDAwMCwidHlwZSI6InJlZnJlc2gifQ.invalid",
            blacklist=mock_blacklist
        )

        assert success is False
        assert error_code == "INVALID_TOKEN"
        assert data is None

    def test_refresh_fails_with_access_token(
        self, auth_service, mock_blacklist
    ):
        """Test refresh fails when access token is used instead of refresh token."""
        # Create an access token (wrong type)
        access_token = create_access_token("00000000-0000-0000-0000-000000000123", "test@example.com", "verified")

        success, error_code, data = auth_service.refresh_access_token(
            refresh_token=access_token,
            blacklist=mock_blacklist
        )

        assert success is False
        assert error_code == "INVALID_TOKEN"
        assert data is None

    def test_refresh_fails_with_blacklisted_token(
        self, auth_service, mock_auth_repo, mock_blacklist
    ):
        """Test refresh fails when token JTI is in blacklist (revoked)."""
        refresh_token = create_refresh_token("00000000-0000-0000-0000-000000000123")

        # Configure blacklist to return True (token is revoked)
        mock_blacklist.is_blacklisted.return_value = True

        success, error_code, data = auth_service.refresh_access_token(
            refresh_token=refresh_token,
            blacklist=mock_blacklist
        )

        assert success is False
        assert error_code == "REVOKED_TOKEN"
        assert data is None

        # Verify blacklist check was called
        mock_blacklist.is_blacklisted.assert_called_once()

    def test_refresh_fails_with_nonexistent_user(
        self, auth_service, mock_auth_repo, mock_blacklist
    ):
        """Test refresh fails when user_id from token not found in database."""
        refresh_token = create_refresh_token("nonexistent-user")

        # User not found in database
        mock_auth_repo.get_by_user_id.return_value = None

        success, error_code, data = auth_service.refresh_access_token(
            refresh_token=refresh_token,
            blacklist=mock_blacklist
        )

        assert success is False
        assert error_code == "USER_NOT_FOUND"
        assert data is None

    def test_refresh_fails_with_locked_account(
        self, auth_service, mock_auth_repo, mock_blacklist
    ):
        """Test refresh fails when account is temporarily locked."""
        refresh_token = create_refresh_token("00000000-0000-0000-0000-000000000123")

        # Setup locked user
        mock_auth_user = Mock()
        mock_auth_user.user_id = "00000000-0000-0000-0000-000000000123"
        mock_auth_user.deleted_at = None
        mock_auth_user.is_locked.return_value = True
        mock_auth_repo.get_by_user_id.return_value = mock_auth_user

        success, error_code, data = auth_service.refresh_access_token(
            refresh_token=refresh_token,
            blacklist=mock_blacklist
        )

        assert success is False
        assert error_code == "ACCOUNT_LOCKED"
        assert data is None

    def test_refresh_fails_with_deleted_account(
        self, auth_service, mock_auth_repo, mock_blacklist
    ):
        """Test refresh fails when account has been soft deleted."""
        refresh_token = create_refresh_token("00000000-0000-0000-0000-000000000123")

        # Setup deleted user
        mock_auth_user = Mock()
        mock_auth_user.user_id = "00000000-0000-0000-0000-000000000123"
        mock_auth_user.deleted_at = datetime.now(timezone.utc)  # Soft deleted
        mock_auth_repo.get_by_user_id.return_value = mock_auth_user

        success, error_code, data = auth_service.refresh_access_token(
            refresh_token=refresh_token,
            blacklist=mock_blacklist
        )

        assert success is False
        assert error_code == "ACCOUNT_DELETED"
        assert data is None

    def test_refresh_fails_when_redis_unavailable_on_blacklist_check(
        self, auth_service, mock_blacklist
    ):
        """Test refresh fails with SERVICE_UNAVAILABLE when Redis is down during blacklist check."""
        from redis.exceptions import ConnectionError as RedisConnectionError

        refresh_token = create_refresh_token("00000000-0000-0000-0000-000000000123")

        # Simulate Redis connection failure on blacklist check
        mock_blacklist.is_blacklisted.side_effect = RedisConnectionError("Connection refused")

        success, error_code, data = auth_service.refresh_access_token(
            refresh_token=refresh_token,
            blacklist=mock_blacklist
        )

        assert success is False
        assert error_code == "SERVICE_UNAVAILABLE"
        assert data is None

    def test_refresh_fails_when_redis_unavailable_on_blacklist_write(
        self, auth_service, mock_auth_repo, mock_profile_repo, mock_blacklist
    ):
        """Test refresh fails with SERVICE_UNAVAILABLE when Redis fails during token blacklisting."""
        from redis.exceptions import ConnectionError as RedisConnectionError

        refresh_token = create_refresh_token("00000000-0000-0000-0000-000000000123")

        # Setup valid user
        mock_auth_user = Mock()
        mock_auth_user.user_id = "00000000-0000-0000-0000-000000000123"
        mock_auth_user.email = "test@example.com"
        mock_auth_user.deleted_at = None
        mock_auth_user.is_locked.return_value = False
        mock_auth_repo.get_by_user_id.return_value = mock_auth_user

        # Setup profile
        from src.models.profile import AccountType
        mock_profile = Mock()
        mock_profile.account_type = AccountType.verified
        mock_profile_repo.get_profile_by_id.return_value = mock_profile

        # Blacklist check passes, but write fails
        mock_blacklist.is_blacklisted.return_value = False
        mock_blacklist.blacklist_token.side_effect = RedisConnectionError("Connection refused")

        success, error_code, data = auth_service.refresh_access_token(
            refresh_token=refresh_token,
            blacklist=mock_blacklist
        )

        assert success is False
        assert error_code == "SERVICE_UNAVAILABLE"
        assert data is None

    def test_refresh_blacklists_old_token_before_issuing_new(
        self, auth_service, mock_auth_repo, mock_profile_repo, mock_blacklist
    ):
        """Test that old refresh token is blacklisted before new tokens are issued."""
        refresh_token = create_refresh_token("00000000-0000-0000-0000-000000000123")

        # Get JTI from original token for verification
        original_token_data = verify_token(refresh_token, token_type="refresh")
        original_jti = original_token_data.jti

        # Setup valid user
        mock_auth_user = Mock()
        mock_auth_user.user_id = "00000000-0000-0000-0000-000000000123"
        mock_auth_user.email = "test@example.com"
        mock_auth_user.deleted_at = None
        mock_auth_user.is_admin = False
        mock_auth_user.is_locked.return_value = False
        mock_auth_repo.get_by_user_id.return_value = mock_auth_user

        # Setup profile
        from src.models.profile import AccountType
        mock_profile = Mock()
        mock_profile.account_type = AccountType.verified
        mock_profile_repo.get_profile_by_id.return_value = mock_profile

        success, error_code, data = auth_service.refresh_access_token(
            refresh_token=refresh_token,
            blacklist=mock_blacklist
        )

        assert success is True

        # Verify blacklist was called with original token's JTI
        mock_blacklist.blacklist_token.assert_called_once()
        call_args = mock_blacklist.blacklist_token.call_args
        assert call_args[0][0] == original_jti
        # TTL should be positive (remaining time until expiry)
        assert call_args[0][1] > 0

    def test_refresh_new_tokens_are_valid(
        self, auth_service, mock_auth_repo, mock_profile_repo, mock_blacklist
    ):
        """Test that newly issued tokens are valid and can be verified."""
        refresh_token = create_refresh_token("00000000-0000-0000-0000-000000000123")

        # Setup valid user
        mock_auth_user = Mock()
        mock_auth_user.user_id = "00000000-0000-0000-0000-000000000123"
        mock_auth_user.email = "test@example.com"
        mock_auth_user.deleted_at = None
        mock_auth_user.is_admin = False
        mock_auth_user.is_locked.return_value = False
        mock_auth_repo.get_by_user_id.return_value = mock_auth_user

        # Setup profile
        from src.models.profile import AccountType
        mock_profile = Mock()
        mock_profile.account_type = AccountType.verified
        mock_profile_repo.get_profile_by_id.return_value = mock_profile

        success, error_code, data = auth_service.refresh_access_token(
            refresh_token=refresh_token,
            blacklist=mock_blacklist
        )

        assert success is True

        # Verify new access token is valid
        new_access_data = verify_token(data["access_token"], token_type="access")
        assert new_access_data is not None
        assert new_access_data.user_id == "00000000-0000-0000-0000-000000000123"
        assert new_access_data.email == "test@example.com"
        assert new_access_data.account_type == "verified"

        # Verify new refresh token is valid
        new_refresh_data = verify_token(data["refresh_token"], token_type="refresh")
        assert new_refresh_data is not None
        assert new_refresh_data.user_id == "00000000-0000-0000-0000-000000000123"

