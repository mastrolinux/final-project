"""
Authentication API Endpoints

REST API endpoints for user authentication, registration, and email verification.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.core.database import get_db
from src.repositories.auth_repository import AuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.repositories.audit_repository import AuditRepository
from src.services.auth_service import AuthService
from src.services.audit_service import AuditService
from src.schemas.auth import (
    RegisterRequest, RegisterResponse,
    LoginRequest, LoginResponse,
    VerifyEmailRequest, VerifyEmailResponse,
    RequestPasswordResetRequest, RequestPasswordResetResponse,
    ResetPasswordRequest, ResetPasswordResponse,
    ResendVerificationRequest, ResendVerificationResponse,
    RefreshTokenRequest, RefreshTokenResponse,
    RestoreAccountRequest, RestoreAccountResponse,
    RestoreAccountConfirmRequest, RestoreAccountConfirmResponse,
    SetPasswordRequest, SetPasswordResponse,
)
from src.core.redis_client import TokenBlacklist, get_blacklist
from src.api.dependencies.auth import get_current_user, require_verified_user
from src.models.auth import AuthUser


router = APIRouter()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """
    Dependency to get AuthService instance.

    Creates service with auth, profile repositories and audit service.
    """
    auth_repo = AuthRepository(db)
    profile_repo = ProfileRepository(db)
    audit_repo = AuditRepository(db)
    audit_service = AuditService(audit_repo)
    return AuthService(auth_repo, profile_repo, audit_service=audit_service)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Register a new user account with email and password authentication"
)
def register(
    request: RegisterRequest,
    http_request: Request,
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
    
    **Password Requirements (NIST SP 800-63B):**
    - Minimum 8 characters
    - Must not be a commonly used password

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

        # Step 0: Check for recoverable soft-deleted account before
        # attempting profile creation. The unique constraint on
        # primary_email would otherwise raise IntegrityError for
        # soft-deleted rows (which still exist in the table).
        auth_repo = AuthRepository(db)
        deleted_user = auth_repo.get_by_email_including_deleted(
            request.email
        )
        if deleted_user and deleted_user.deleted_at is not None:
            from datetime import timedelta, timezone, datetime
            from src.core.config import settings
            retention_days = settings.DELETION_RETENTION_DAYS
            deleted_at = deleted_user.deleted_at
            if deleted_at.tzinfo is None:
                deleted_at = deleted_at.replace(tzinfo=timezone.utc)
            permanent_date = (
                deleted_at + timedelta(days=retention_days)
            )
            if permanent_date > datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "detail": (
                            "A recoverable account exists for this email"
                        ),
                        "code": "ACCOUNT_RECOVERABLE",
                        "account_recoverable": True,
                        "permanent_deletion_date": (
                            permanent_date.isoformat()
                        ),
                        "restore_endpoint": (
                            "/api/v1/auth/restore-account"
                        ),
                    },
                )

        # Step 1: Create base profile
        try:
            base_profile = profile_repo.create_profile(
                account_type=request.account_type,
                primary_email=request.email,
                preferred_language=request.preferred_language,
                legal_name=request.preferred_name
            )
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Step 2: Create auth user with auth service
        auth_repo = AuthRepository(db)
        audit_repo = AuditRepository(db)
        audit_service = AuditService(audit_repo)
        auth_service = AuthService(auth_repo, profile_repo, audit_service=audit_service)

        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")

        success, error, data = auth_service.register_user(
            email=request.email,
            password=request.password,
            user_id=str(base_profile.user_id),
            display_name=request.preferred_name,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if not success:
            # Rollback profile creation if auth user creation fails
            db.rollback()

            if error == "ACCOUNT_RECOVERABLE":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "detail": "A recoverable account exists for this email",
                        "code": "ACCOUNT_RECOVERABLE",
                        "account_recoverable": True,
                        "permanent_deletion_date": data.get(
                            "permanent_deletion_date"
                        ),
                        "restore_endpoint": "/api/v1/auth/restore-account",
                    },
                )
            elif "already registered" in error:
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
    http_request: Request,
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
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")

    success, error, data = service.login(
        email=request.email,
        password=request.password,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not success:
        if error == "ACCOUNT_DELETED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "detail": "Account scheduled for deletion",
                    "code": "ACCOUNT_DELETED",
                    "deletion_scheduled_at": data.get("deletion_scheduled_at"),
                    "permanent_deletion_date": data.get(
                        "permanent_deletion_date"
                    ),
                    "recovery_info": data.get("recovery_info"),
                },
            )
        elif "locked" in error.lower():
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
    
    **Password Requirements (NIST SP 800-63B):**
    - Minimum 8 characters
    - Must not be a commonly used password

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


def get_token_blacklist() -> TokenBlacklist:
    """
    Dependency to get TokenBlacklist singleton instance.

    Creates Redis connection on first call if Redis is enabled.

    Returns:
        TokenBlacklist singleton instance

    Raises:
        HTTPException 503: If Redis is unavailable or disabled
    """
    try:
        return get_blacklist()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token refresh service temporarily unavailable"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token refresh service temporarily unavailable"
        )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Exchange valid refresh token for new access and refresh tokens"
)
def refresh_token(
    request: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
    blacklist: TokenBlacklist = Depends(get_token_blacklist)
):
    """
    Refresh Access Token

    Exchanges a valid refresh token for new access and refresh tokens.
    Implements refresh token rotation: the old refresh token is invalidated.

    **Process:**
    1. Validates refresh token signature and expiry
    2. Checks token has not been revoked (blacklisted)
    3. Verifies user account is active (not locked or deleted)
    4. Invalidates old refresh token (adds to blacklist)
    5. Issues new access token (1 hour) and refresh token (30 days)

    **Token Rotation:**
    Each refresh operation invalidates the old refresh token and issues a new one.
    This limits the damage from token theft: a stolen token can only be used once.

    **Security:**
    - Refresh tokens are single-use (rotation)
    - Reusing an old refresh token indicates potential token theft
    - Account status validated on each refresh
    - Redis blacklist ensures immediate token invalidation

    **Example Request:**
    ```json
    {
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```

    **Errors:**
    - 401: Invalid, expired, or revoked token
    - 403: Account locked or deleted
    - 503: Token blacklist service unavailable
    """
    success, error_code, data = service.refresh_access_token(
        refresh_token=request.refresh_token,
        blacklist=blacklist
    )

    if not success:
        # Map error codes to HTTP status codes
        # Use generic messages for 401 to prevent token enumeration
        if error_code in ("INVALID_TOKEN", "REVOKED_TOKEN", "USER_NOT_FOUND"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        elif error_code == "ACCOUNT_LOCKED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account temporarily locked"
            )
        elif error_code == "ACCOUNT_DELETED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account has been deactivated"
            )
        elif error_code == "SERVICE_UNAVAILABLE":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Token refresh service temporarily unavailable"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh failed"
            )

    return RefreshTokenResponse(**data)


@router.post(
    "/restore-account",
    response_model=RestoreAccountResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request Account Restoration",
    description=(
        "Request restoration of a soft-deleted account. Sends a time-limited "
        "restoration token via email. Always returns 202 regardless of whether "
        "the email exists (prevents enumeration)."
    ),
)
def request_restore_account(
    request: RestoreAccountRequest,
    service: AuthService = Depends(get_auth_service),
):
    """Request account restoration email."""
    service.request_account_restoration(request.email)
    return RestoreAccountResponse(
        message=(
            "If a recoverable account exists for this email, "
            "a restoration link has been sent."
        )
    )


@router.post(
    "/restore-account/confirm",
    response_model=RestoreAccountConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm Account Restoration",
    description=(
        "Confirm account restoration with the token received via email "
        "and set a new password. Returns JWT tokens on success."
    ),
)
def confirm_restore_account(
    request: RestoreAccountConfirmRequest,
    http_request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """Confirm account restoration with token and optional password.

    Password is required for email/password users but not for OAuth users.
    """
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")

    success, error_code, data = service.confirm_account_restoration(
        token=request.token,
        new_password=request.new_password,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not success:
        if error_code == "ACCOUNT_PERMANENTLY_DELETED":
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={
                    "detail": "Account permanently deleted. Grace period expired.",
                    "code": "ACCOUNT_PERMANENTLY_DELETED",
                },
            )
        elif error_code == "INVALID_RESTORATION_TOKEN":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "detail": "Invalid or expired restoration token",
                    "code": "INVALID_RESTORATION_TOKEN",
                },
            )
        elif error_code == "PASSWORD_REQUIRED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "detail": "Password is required for email/password accounts",
                    "code": "PASSWORD_REQUIRED",
                },
            )
        elif error_code == "PROFILE_NOT_FOUND":
            # Data integrity issue - auth_user exists but base_profile doesn't
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "detail": data.get("message", "Profile not found during restoration"),
                    "code": "PROFILE_NOT_FOUND",
                    "user_id": data.get("user_id") if data else None,
                },
            )
        else:
            # Password validation error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_code,
            )

    return RestoreAccountConfirmResponse(**data)


@router.post(
    "/set-password",
    response_model=SetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Set Password for OAuth User",
    description=(
        "Allows an OAuth-registered user (Google, etc.) to set a password "
        "so they can also login via email/password. Requires JWT authentication. "
        "Can only be used once per user; after setting a password, use "
        "reset-password to change it."
    ),
)
def set_password(
    request: SetPasswordRequest,
    http_request: Request,
    current_user: AuthUser = Depends(require_verified_user),
    service: AuthService = Depends(get_auth_service),
):
    """
    Set Password for OAuth User

    Allows an OAuth-registered user to add password-based authentication.
    After setting a password, the user can login via both OAuth and
    email/password.

    **Preconditions:**
    - User must be authenticated (JWT access token required)
    - User must have registered via OAuth (provider is not None)
    - User must not have already set a custom password

    **Password Requirements (NIST SP 800-63B):**
    - Minimum 8 characters
    - Must not be a commonly used password

    **Errors:**
    - 400: Not an OAuth user, or weak password
    - 401: Not authenticated
    - 409: Password already set (use reset-password instead)
    """
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")

    success, error_code, data = service.set_password(
        user_id=str(current_user.user_id),
        new_password=request.new_password,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not success:
        if error_code == "USER_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        elif error_code == "NOT_OAUTH_USER":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "detail": (
                        "Password can only be set for OAuth-registered users. "
                        "Use reset-password to change an existing password."
                    ),
                    "code": "NOT_OAUTH_USER",
                }
            )
        elif error_code == "PASSWORD_ALREADY_SET":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "detail": "Password already set. Use reset-password to change it.",
                    "code": "PASSWORD_ALREADY_SET",
                }
            )
        else:
            # Password validation error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_code
            )

    return SetPasswordResponse(**data)

