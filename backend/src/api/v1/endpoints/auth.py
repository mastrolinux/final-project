"""
Authentication API Endpoints

REST API endpoints for user authentication, registration, and email verification.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.repositories.auth_repository import AuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.services.auth_service import AuthService
from src.schemas.auth import (
    RegisterRequest, RegisterResponse,
    LoginRequest, LoginResponse,
    VerifyEmailRequest, VerifyEmailResponse,
    RequestPasswordResetRequest, RequestPasswordResetResponse,
    ResetPasswordRequest, ResetPasswordResponse,
    ResendVerificationRequest, ResendVerificationResponse
)


router = APIRouter()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """
    Dependency to get AuthService instance.
    
    Creates service with auth and profile repositories.
    """
    auth_repo = AuthRepository(db)
    profile_repo = ProfileRepository(db)
    return AuthService(auth_repo, profile_repo)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Register a new user account with email and password authentication"
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register New User Account
    
    Creates a new user with email/password authentication and sends verification email.
    
    **Process:**
    1. Validates email format and password strength
    2. Creates base profile record
    3. Creates auth user record with hashed password
    4. Sends verification email via Mailpit/SMTP (async)
    5. Returns user data with verification pending
    
    **Password Requirements:**
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    
    **Email Verification:**
    - User receives email with verification link
    - Link expires in 24 hours
    - Check Mailpit UI at http://127.0.0.1:54324 (local dev)
    
    **Transaction Safety:**
    - Profile and auth user creation wrapped in database transaction
    - Rollback on failure ensures data consistency
    
    **Example Request:**
    ```json
    {
      "email": "user@example.com",
      "password": "SecurePass123!",
      "preferred_name": "John Doe",
      "account_type": "unverified",
      "preferred_language": "en"
    }
    ```
    
    **Errors:**
    - 400: Weak password or validation error
    - 409: Email already registered
    """
    try:
        # Create profile repository
        profile_repo = ProfileRepository(db)
        
        # Step 1: Create base profile
        base_profile = profile_repo.create_profile(
            account_type=request.account_type,
            primary_email=request.email,
            preferred_language=request.preferred_language,
            legal_name=request.preferred_name
        )
        
        # Step 2: Create auth user with auth service
        auth_repo = AuthRepository(db)
        auth_service = AuthService(auth_repo, profile_repo)
        
        success, error, data = auth_service.register_user(
            email=request.email,
            password=request.password,
            user_id=str(base_profile.user_id),
            display_name=request.preferred_name
        )
        
        if not success:
            # Rollback profile creation if auth user creation fails
            db.rollback()
            
            if "already registered" in error:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=error
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error
                )
        
        return RegisterResponse(**data)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate user and return JWT tokens"
)
def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    User Login
    
    Authenticates user with email and password, returns JWT tokens.
    
    **Process:**
    1. Validates credentials against Argon2id hash
    2. Checks if account is locked (5 failed attempts = 15 min lock)
    3. Generates JWT access token (1 hour expiry)
    4. Generates JWT refresh token (30 days expiry)
    5. Resets failed login counter on success
    
    **Response:**
    - access_token: Use for API requests (Authorization: Bearer token)
    - refresh_token: Use to get new access token when expired
    - expires_in: Access token expiry in seconds (3600 = 1 hour)
    
    **Security:**
    - Password verified with constant-time comparison
    - Failed attempts tracked and logged
    - Account locked after 5 failed attempts
    - Generic error message (doesn't reveal if email exists)
    
    **Example Request:**
    ```json
    {
      "email": "user@example.com",
      "password": "SecurePass123!"
    }
    ```
    
    **Errors:**
    - 401: Invalid email or password
    - 403: Account locked due to failed login attempts
    """
    success, error, data = service.login(
        email=request.email,
        password=request.password
    )
    
    if not success:
        if "locked" in error.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error
            )
    
    return LoginResponse(**data)


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Email",
    description="Verify email address with token from email"
)
def verify_email(
    request: VerifyEmailRequest,
    service: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db)
):
    """
    Verify Email Address
    
    Verifies user email with token sent via email.
    
    **Process:**
    1. Validates token exists and not expired
    2. Updates auth_users.is_email_verified = true
    3. Clears verification token
    4. Returns success message
    
    **Token:**
    - Sent via email during registration
    - Expires in 24 hours
    - Can only be used once
    - Check Mailpit UI at http://127.0.0.1:54324 to get token (local dev)
    
    **Example Request:**
    ```json
    {
      "token": "abc123def456ghi789jkl012mno345pqr"
    }
    ```
    
    **Errors:**
    - 400: Invalid or expired token
    - 404: Token not found
    """
    success, error = service.verify_email(request.token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Get user info for response
    auth_repo = AuthRepository(db)
    auth_user = auth_repo.get_by_verification_token(request.token)
    
    # Token might be cleared, so get by email from recently verified user
    # This is a bit hacky - in production would track this differently
    # For now, return success without specific user info
    return VerifyEmailResponse(
        message="Email verified successfully",
        email="",  # Email already verified, token cleared
        user_id=""
    )


@router.post(
    "/request-reset",
    response_model=RequestPasswordResetResponse,
    status_code=status.HTTP_200_OK,
    summary="Request Password Reset",
    description="Request password reset email"
)
def request_password_reset(
    request: RequestPasswordResetRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    Request Password Reset
    
    Sends password reset email with token.
    
    **Process:**
    1. Generates secure reset token
    2. Stores token in database (1 hour expiry)
    3. Sends reset email via Mailpit/SMTP (async)
    4. Always returns success (prevents email enumeration)
    
    **Security:**
    - Returns success even if email doesn't exist
    - Prevents attackers from discovering registered emails
    - Token expires in 1 hour
    - Check Mailpit UI at http://127.0.0.1:54324 for email (local dev)
    
    **Example Request:**
    ```json
    {
      "email": "user@example.com"
    }
    ```
    
    **Response:**
    Always 200 OK with generic message, regardless of whether email exists.
    """
    success, error = service.request_password_reset(request.email)
    
    # Always return success for security (prevent email enumeration)
    return RequestPasswordResetResponse(
        message="If the email exists, a password reset link has been sent. Please check your inbox."
    )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset Password",
    description="Reset password with token from email"
)
def reset_password(
    request: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    Reset Password
    
    Resets user password with token from email.
    
    **Process:**
    1. Validates reset token exists and not expired
    2. Validates new password strength
    3. Hashes new password with Argon2id
    4. Updates password in database
    5. Clears reset token
    
    **Password Requirements:**
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    
    **Token:**
    - Sent via email during password reset request
    - Expires in 1 hour
    - Can only be used once
    - Check Mailpit UI at http://127.0.0.1:54324 for email (local dev)
    
    **Example Request:**
    ```json
    {
      "token": "abc123def456ghi789jkl012mno345pqr",
      "new_password": "NewSecurePass123!"
    }
    ```
    
    **Errors:**
    - 400: Invalid/expired token or weak password
    - 404: Token not found
    """
    success, error = service.reset_password(request.token, request.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return ResetPasswordResponse(
        message="Password reset successfully. You can now login with your new password."
    )


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend Verification Email",
    description="Resend email verification link"
)
def resend_verification(
    request: ResendVerificationRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    Resend Verification Email
    
    Resends email verification link to user.
    
    **Process:**
    1. Checks if email exists and not already verified
    2. Generates new verification token
    3. Sends verification email via Mailpit/SMTP (async)
    4. Returns success message
    
    **Use Case:**
    - User didn't receive original verification email
    - Original verification token expired (24 hours)
    - User needs new verification link
    
    **Token:**
    - New token generated (old token invalidated)
    - Expires in 24 hours
    - Check Mailpit UI at http://127.0.0.1:54324 for email (local dev)
    
    **Example Request:**
    ```json
    {
      "email": "user@example.com"
    }
    ```
    
    **Errors:**
    - 400: Email already verified
    - 404: Email not found
    """
    success, error = service.resend_verification_email(request.email)
    
    if not success:
        if "already verified" in error.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error
            )
    
    return ResendVerificationResponse(
        message="Verification email sent. Please check your inbox."
    )



