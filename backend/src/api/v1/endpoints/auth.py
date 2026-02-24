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
    """Dependency to get AuthService instance."""
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
    """Register a new user with email/password authentication."""
    try:
        profile_repo = ProfileRepository(db)

        # Check for recoverable soft-deleted account before profile creation;
        # the unique constraint on primary_email covers soft-deleted rows.
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
    """Authenticate user with email/password and return JWT tokens."""
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
    """Verify user email with token sent during registration."""
    success, error = service.verify_email(request.token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Token is cleared on verification, so user info is unavailable here
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
    """Send password reset email. Returns success even for non-existent addresses."""
    success, error = service.request_password_reset(request.email)
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
    """Reset user password with token from email."""
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
    """Resend email verification link to user."""
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
    """Dependency to get TokenBlacklist singleton instance."""
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
    """Exchange valid refresh token for new tokens (with rotation)."""
    success, error_code, data = service.refresh_access_token(
        refresh_token=request.refresh_token,
        blacklist=blacklist
    )

    if not success:
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
    """Confirm account restoration. Password required for email/password users, not OAuth."""
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
    """Allow an OAuth-registered user to add password-based authentication."""
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

