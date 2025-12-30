"""
Authentication Service

Business logic layer for authentication operations.
Handles user registration, login, email verification, and password reset.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple
import secrets

from src.repositories.auth_repository import AuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.core.security import (
    hash_password, 
    verify_password, 
    validate_password_strength,
    create_access_token, 
    create_refresh_token
)
from src.tasks.email_tasks import send_verification_email, send_password_reset_email


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, auth_repo: AuthRepository, profile_repo: ProfileRepository):
        """
        Initialize auth service with repositories.
        
        Args:
            auth_repo: Authentication repository
            profile_repo: Profile repository (to get account_type)
        """
        self.auth_repo = auth_repo
        self.profile_repo = profile_repo
    
    def register_user(
        self, 
        email: str, 
        password: str, 
        user_id: str,
        display_name: str
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Register new user with email and password.
        
        Process:
        1. Check if email already exists
        2. Validate password strength
        3. Hash password with Argon2id
        4. Create auth_users record
        5. Generate verification token
        6. Send verification email (async via Celery)
        
        Args:
            email: User email address
            password: Plain text password
            user_id: User ID from base_profiles (must exist)
            display_name: User's display name for email personalization
            
        Returns:
            Tuple of (success, error_message, auth_data)
            auth_data contains: user_id, email, is_email_verified
        """
        # Check if email already exists
        existing = self.auth_repo.get_by_email(email)
        if existing:
            return False, "Email already registered", None
        
        # Validate password strength
        valid, message = validate_password_strength(password)
        if not valid:
            return False, message, None
        
        # Hash password with Argon2id
        password_hash = hash_password(password)
        
        # Create auth user
        auth_user = self.auth_repo.create(email, password_hash, user_id)
        
        # Generate secure verification token
        verification_token = secrets.token_urlsafe(32)
        self.auth_repo.set_verification_token(user_id, verification_token, expires_hours=24)
        
        # Send verification email asynchronously
        send_verification_email.delay(email, verification_token, display_name)
        
        return True, None, {
            "user_id": str(auth_user.user_id),
            "email": auth_user.email,
            "is_email_verified": False,
            "message": "Registration successful. Please check your email to verify your account."
        }
    
    def login(
        self, 
        email: str, 
        password: str
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Authenticate user and return JWT tokens.
        
        Process:
        1. Get auth user by email
        2. Check if account is locked
        3. Verify password
        4. Reset failed login attempts on success
        5. Get account type from base_profiles
        6. Generate access and refresh tokens
        
        Args:
            email: User email address
            password: Plain text password
            
        Returns:
            Tuple of (success, error_message, token_data)
            token_data contains: access_token, refresh_token, token_type, expires_in, user_id, email
        """
        # Get auth user
        auth_user = self.auth_repo.get_by_email(email)
        if not auth_user:
            return False, "Invalid email or password", None
        
        # Check if account is locked
        if auth_user.is_locked():
            return False, "Account temporarily locked due to failed login attempts. Please try again later.", None
        
        # Verify password
        if not verify_password(password, auth_user.password_hash):
            # Increment failed login attempts
            self.auth_repo.increment_failed_login(str(auth_user.user_id))
            return False, "Invalid email or password", None
        
        # Reset failed login attempts on successful login
        self.auth_repo.reset_failed_login(str(auth_user.user_id))
        
        # Get account type from base_profiles
        base_profile = self.profile_repo.get_profile_by_id(auth_user.user_id)
        account_type = base_profile.account_type.value if base_profile else "unverified"
        
        # Generate JWT tokens
        access_token = create_access_token(
            str(auth_user.user_id),
            auth_user.email,
            account_type
        )
        refresh_token = create_refresh_token(str(auth_user.user_id))
        
        return True, None, {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600,  # 1 hour
            "user_id": str(auth_user.user_id),
            "email": auth_user.email,
            "is_email_verified": auth_user.is_email_verified,
            "account_type": account_type
        }
    
    def verify_email(self, token: str) -> Tuple[bool, Optional[str]]:
        """
        Verify email with verification token.
        
        Process:
        1. Find auth user by verification token
        2. Check if token exists and not expired
        3. Update verification status
        4. Clear verification token
        
        Args:
            token: Email verification token
            
        Returns:
            Tuple of (success, error_message)
        """
        # Find auth user by verification token
        auth_user = self.auth_repo.get_by_verification_token(token)
        if not auth_user:
            return False, "Invalid or expired verification token"
        
        # Check if token is valid and not expired
        if not auth_user.is_verification_token_valid(token):
            return False, "Verification token has expired. Please request a new one."
        
        # Update verification status
        self.auth_repo.update_verification_status(str(auth_user.user_id), verified=True)
        
        return True, None
    
    def request_password_reset(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Request password reset email.
        
        Process:
        1. Find auth user by email
        2. Generate secure reset token
        3. Store token with 1-hour expiry
        4. Send reset email (async via Celery)
        
        Note: Always returns success even if email doesn't exist (security best practice)
        
        Args:
            email: User email address
            
        Returns:
            Tuple of (success, error_message)
        """
        # Get auth user
        auth_user = self.auth_repo.get_by_email(email)
        if not auth_user:
            # Return success even if email doesn't exist (prevent email enumeration)
            return True, None
        
        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)
        self.auth_repo.set_reset_token(str(auth_user.user_id), reset_token, expires_hours=1)
        
        # Send reset email asynchronously
        send_password_reset_email.delay(email, reset_token)
        
        return True, None
    
    def reset_password(
        self, 
        token: str, 
        new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Reset password with reset token.
        
        Process:
        1. Find auth user by reset token
        2. Check if token is valid and not expired
        3. Validate new password strength
        4. Hash new password
        5. Update password hash
        6. Clear reset token
        
        Args:
            token: Password reset token
            new_password: New plain text password
            
        Returns:
            Tuple of (success, error_message)
        """
        # Find auth user by reset token
        auth_user = self.auth_repo.get_by_reset_token(token)
        if not auth_user:
            return False, "Invalid or expired reset token"
        
        # Check if token is valid and not expired
        if not auth_user.is_reset_token_valid(token):
            return False, "Reset token has expired. Please request a new one."
        
        # Validate new password strength
        valid, message = validate_password_strength(new_password)
        if not valid:
            return False, message
        
        # Hash new password
        password_hash = hash_password(new_password)
        
        # Update password and clear reset token
        self.auth_repo.update_password(str(auth_user.user_id), password_hash)
        self.auth_repo.clear_reset_token(str(auth_user.user_id))
        
        return True, None
    
    def resend_verification_email(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Resend verification email to user.
        
        Process:
        1. Find auth user by email
        2. Check if already verified
        3. Generate new verification token
        4. Send verification email
        
        Args:
            email: User email address
            
        Returns:
            Tuple of (success, error_message)
        """
        # Get auth user
        auth_user = self.auth_repo.get_by_email(email)
        if not auth_user:
            return False, "Email not found"
        
        # Check if already verified
        if auth_user.is_email_verified:
            return False, "Email is already verified"
        
        # Get user's display name from base_profiles
        base_profile = self.profile_repo.get_profile_by_id(auth_user.user_id)
        display_name = "User" if not base_profile else (base_profile.legal_name or "User")
        
        # Generate new verification token
        verification_token = secrets.token_urlsafe(32)
        self.auth_repo.set_verification_token(str(auth_user.user_id), verification_token, expires_hours=24)
        
        # Send verification email asynchronously
        send_verification_email.delay(email, verification_token, display_name)
        
        return True, None

