"""
Authentication Schemas

Pydantic models for authentication request/response validation.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from src.models.profile import AccountType


class RegisterRequest(BaseModel):
    """
    User registration request schema.
    
    Creates new user with email/password authentication.
    """
    email: EmailStr = Field(
        ...,
        description="User email address (must be unique)"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars, 1 uppercase, 1 lowercase, 1 digit)"
    )
    preferred_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User's preferred display name"
    )
    account_type: AccountType = Field(
        default=AccountType.unverified,
        description="Account type: verified, unverified, or pseudonymous"
    )
    preferred_language: str = Field(
        default="en",
        max_length=10,
        description="Preferred language code (ISO 639-1)"
    )
    
    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, v):
        """Strip whitespace from email."""
        if isinstance(v, str):
            return v.strip().lower()
        return v
    
    @field_validator("preferred_name", mode="before")
    @classmethod
    def strip_name(cls, v):
        """Strip whitespace from name."""
        if isinstance(v, str):
            return v.strip()
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "email": "user@example.com",
                "password": "SecurePass123!",
                "preferred_name": "John Doe",
                "account_type": "unverified",
                "preferred_language": "en"
            }]
        }
    )


class RegisterResponse(BaseModel):
    """User registration response."""
    user_id: str = Field(..., description="Created user ID")
    email: str = Field(..., description="Registered email address")
    is_email_verified: bool = Field(..., description="Email verification status (false for new users)")
    message: str = Field(..., description="Registration success message")
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "is_email_verified": False,
                "message": "Registration successful. Please check your email to verify your account."
            }]
        }
    )


class LoginRequest(BaseModel):
    """User login request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    
    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, v):
        """Strip whitespace from email."""
        if isinstance(v, str):
            return v.strip().lower()
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "email": "user@example.com",
                "password": "SecurePass123!"
            }]
        }
    )


class LoginResponse(BaseModel):
    """User login response with JWT tokens."""
    access_token: str = Field(..., description="JWT access token (1 hour expiry)")
    refresh_token: str = Field(..., description="JWT refresh token (30 days expiry)")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    is_email_verified: bool = Field(..., description="Email verification status")
    account_type: str = Field(..., description="Account type (verified/unverified/pseudonymous)")
    is_admin: bool = Field(..., description="Admin status")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "is_email_verified": True,
                "account_type": "verified",
                "is_admin": False
            }]
        }
    )


class VerifyEmailRequest(BaseModel):
    """Email verification request schema."""
    token: str = Field(
        ...,
        min_length=32,
        description="Email verification token from email"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "token": "abc123def456ghi789jkl012mno345pqr"
            }]
        }
    )


class VerifyEmailResponse(BaseModel):
    """Email verification response."""
    message: str = Field(..., description="Success message")
    email: str = Field(..., description="Verified email address")
    user_id: str = Field(..., description="User ID")
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "message": "Email verified successfully",
                "email": "user@example.com",
                "user_id": "123e4567-e89b-12d3-a456-426614174000"
            }]
        }
    )


class RequestPasswordResetRequest(BaseModel):
    """Password reset request schema."""
    email: EmailStr = Field(..., description="User email address")
    
    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, v):
        """Strip whitespace from email."""
        if isinstance(v, str):
            return v.strip().lower()
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "email": "user@example.com"
            }]
        }
    )


class RequestPasswordResetResponse(BaseModel):
    """Password reset request response."""
    message: str = Field(
        ..., 
        description="Success message (always returned, even if email doesn't exist)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "message": "If the email exists, a password reset link has been sent."
            }]
        }
    )


class ResetPasswordRequest(BaseModel):
    """Password reset with token schema."""
    token: str = Field(
        ...,
        min_length=32,
        description="Password reset token from email"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (min 8 chars, 1 uppercase, 1 lowercase, 1 digit)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "token": "abc123def456ghi789jkl012mno345pqr",
                "new_password": "NewSecurePass123!"
            }]
        }
    )


class ResetPasswordResponse(BaseModel):
    """Password reset response."""
    message: str = Field(..., description="Success message")
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "message": "Password reset successfully. You can now login with your new password."
            }]
        }
    )


class ResendVerificationRequest(BaseModel):
    """Resend verification email request schema."""
    email: EmailStr = Field(..., description="User email address")
    
    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, v):
        """Strip whitespace from email."""
        if isinstance(v, str):
            return v.strip().lower()
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "email": "user@example.com"
            }]
        }
    )


class ResendVerificationResponse(BaseModel):
    """Resend verification response."""
    message: str = Field(..., description="Success message")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "message": "Verification email sent. Please check your inbox."
            }]
        }
    )


class RefreshTokenRequest(BaseModel):
    """
    Refresh token request schema.

    Used to exchange a valid refresh token for new access and refresh tokens.
    Implements refresh token rotation for enhanced security.
    """
    refresh_token: str = Field(
        ...,
        min_length=50,
        description="JWT refresh token obtained from login or previous refresh"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwidG9rZW5fdHlwZSI6InJlZnJlc2gifQ..."
            }]
        }
    )


class RefreshTokenResponse(BaseModel):
    """
    Refresh token response with new tokens.

    Returns new access and refresh tokens. The old refresh token is
    invalidated (blacklisted) to implement token rotation.
    """
    access_token: str = Field(
        ...,
        description="New JWT access token (1 hour expiry)"
    )
    refresh_token: str = Field(
        ...,
        description="New JWT refresh token (30 days expiry)"
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiry in seconds (3600 = 1 hour)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwidG9rZW5fdHlwZSI6ImFjY2VzcyJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwidG9rZW5fdHlwZSI6InJlZnJlc2gifQ...",
                "token_type": "bearer",
                "expires_in": 3600
            }]
        }
    )

