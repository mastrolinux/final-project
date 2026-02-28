"""
Social Authentication API Endpoints

REST API endpoints for OAuth 2.0 social login (Google, GitHub, etc.)
Implements Authorization Code Flow with PKCE for secure authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.repositories.audit_repository import AuditRepository
from src.repositories.auth_repository import AuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.schemas.auth import LoginResponse
from src.services.audit_service import AuditService
from src.services.social_auth_service import (
    AccountLinkingError,
    OAuthProviderNotConfiguredError,
    OAuthStateValidationError,
    OAuthTokenExchangeError,
    OAuthTokenVerificationError,
    SocialAuthService,
)

router = APIRouter(prefix="/social", tags=["Social Authentication"])


def get_social_auth_service(db: Session = Depends(get_db)) -> SocialAuthService:
    """Dependency to get SocialAuthService instance."""
    auth_repo = AuthRepository(db)
    profile_repo = ProfileRepository(db)
    audit_repo = AuditRepository(db)
    audit_service = AuditService(audit_repo)
    return SocialAuthService(auth_repo, profile_repo, audit_service=audit_service)


@router.post(
    "/{provider}/authorize",
    status_code=status.HTTP_200_OK,
    summary="Generate OAuth Authorization URL",
    description="Generate OAuth 2.0 authorization URL with PKCE for social login",
)
def authorize(
    provider: str,
    http_request: Request,
    response: Response,
    service: SocialAuthService = Depends(get_social_auth_service),
):
    """Generate OAuth 2.0 authorization URL with PKCE for social login."""
    try:
        authorization_url, state, code_verifier = service.generate_authorization_url(provider)

        return {
            "authorization_url": authorization_url,
            "state": state,
            "code_verifier": code_verifier,
            "message": (
                "Redirect user to authorization_url."
                " Store code_verifier and state in sessionStorage."
            ),
        }

    except OAuthProviderNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "oauth_not_configured", "message": str(e), "provider": provider},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_provider", "message": str(e), "provider": provider},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "authorization_url_failed",
                "message": f"Failed to generate authorization URL: {str(e)}",
            },
        )


@router.get(
    "/{provider}/callback",
    response_model=LoginResponse,
    summary="OAuth Callback Endpoint",
    description="Handle OAuth 2.0 provider callback and issue JWT tokens",
)
async def callback(
    provider: str,
    code: str,
    state: str,
    code_verifier: str,
    expected_state: str,
    http_request: Request,
    service: SocialAuthService = Depends(get_social_auth_service),
):
    """Handle OAuth provider callback, verify code, and issue JWT tokens."""
    try:
        client_ip = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("User-Agent")

        token_response = service.exchange_code_for_token(
            provider=provider,
            code=code,
            code_verifier=code_verifier,
            state=state,
            expected_state=expected_state,
        )

        id_token = token_response.get("id_token")
        if not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "missing_id_token", "message": "Provider did not return ID token"},
            )

        claims = service.verify_google_id_token(id_token)

        provider_id = claims.get("sub")
        email = claims.get("email")
        display_name = claims.get("name", email)
        email_verified = claims.get("email_verified", False)

        (
            access_token,
            refresh_token,
            user_id,
            is_new_user,
            account_type,
            is_email_verified,
            is_admin,
            oauth_provider,
            has_custom_password,
        ) = service.authenticate_or_create_user(
            provider=provider,
            provider_id=provider_id,
            email=email,
            display_name=display_name,
            email_verified=email_verified,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=1800,  # 30 minutes
            user_id=user_id,
            email=email,
            is_email_verified=is_email_verified,
            account_type=account_type,
            is_admin=is_admin,
            provider=oauth_provider,
            has_custom_password=has_custom_password,
        )

    except OAuthStateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_state", "message": str(e)},
        )
    except OAuthTokenExchangeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "token_exchange_failed", "message": str(e)},
        )
    except OAuthTokenVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "token_verification_failed", "message": str(e)},
        )
    except AccountLinkingError as e:
        error_message = str(e)

        if "ACCOUNT_RECOVERABLE|" in error_message:
            parts = error_message.split("ACCOUNT_RECOVERABLE|")
            permanent_deletion_date = parts[1] if len(parts) > 1 else None

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "ACCOUNT_RECOVERABLE",
                    "message": "This account was previously deleted and can be restored.",
                    "permanent_deletion_date": permanent_deletion_date,
                    "restore_endpoint": "/api/v1/auth/restore-account",
                },
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "account_linking_required", "message": error_message},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "callback_failed", "message": f"OAuth callback failed: {str(e)}"},
        )
