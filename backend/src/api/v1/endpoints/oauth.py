"""
OAuth 2.1 Endpoints

REST API endpoints for OAuth 2.1 authorization server.
Implements Authorization Code Flow with mandatory PKCE.
"""

from typing import Optional, List
from uuid import UUID
from fastapi import (
    APIRouter, Depends, HTTPException, status, Query, Request,
    Form, Header, Response
)
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.core.database import get_db
from src.repositories.oauth_repository import OAuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.repositories.context_repository import ContextRepository
from src.services.oauth_service import (
    OAuthService,
    OAuthServiceError,
    InvalidClientError,
    InvalidGrantError,
    InvalidRequestError,
    InvalidScopeError,
    AccessDeniedError
)
from src.schemas.oauth import (
    AuthorizationRequest,
    TokenRequest,
    TokenResponse,
    IntrospectionRequest,
    IntrospectionResponse,
    RevocationRequest,
    UserInfoResponse,
    OAuthServerMetadata,
    ConsentRequest,
    ConsentResponse,
    ConsentListResponse,
    ScopeInfo,
    ScopeListResponse,
    TokenErrorResponse,
    GrantType
)
from src.models.context import ContextType


router = APIRouter()


def get_oauth_service(db: Session = Depends(get_db)) -> OAuthService:
    """Dependency to get OAuthService instance"""
    oauth_repo = OAuthRepository(db)
    profile_repo = ProfileRepository(db)
    context_repo = ContextRepository(db)
    return OAuthService(oauth_repo, profile_repo, context_repo)


# =============================================================================
# OAuth 2.1 Discovery Endpoint
# =============================================================================

@router.get(
    "/.well-known/oauth-authorization-server",
    response_model=OAuthServerMetadata,
    summary="OAuth Server Metadata",
    description="Returns OAuth 2.0 Authorization Server Metadata (RFC 8414)"
)
def get_oauth_metadata(request: Request):
    """
    Return OAuth server metadata for discovery.
    
    Clients can use this to automatically configure endpoints.
    """
    base_url = str(request.base_url).rstrip('/')
    
    return OAuthServerMetadata(
        issuer=base_url,
        authorization_endpoint=f"{base_url}/oauth/authorize",
        token_endpoint=f"{base_url}/oauth/token",
        userinfo_endpoint=f"{base_url}/oauth/userinfo",
        introspection_endpoint=f"{base_url}/oauth/introspect",
        revocation_endpoint=f"{base_url}/oauth/revoke",
        scopes_supported=[
            "openid",
            "profile:read:basic",
            "profile:read:email",
            "profile:read:phone",
            "profile:read:full",
            "profile:write",
            "contexts:read",
            "contexts:professional:read",
            "contexts:social:read",
            "contexts:legal:read",
            "contexts:healthcare:read",
            "email",
            "phone",
            "offline_access"
        ],
        response_types_supported=["code"],
        response_modes_supported=["query"],
        grant_types_supported=["authorization_code", "refresh_token"],
        token_endpoint_auth_methods_supported=[
            "none", "client_secret_post", "client_secret_basic"
        ],
        code_challenge_methods_supported=["S256"],
        subject_types_supported=["public"],
        id_token_signing_alg_values_supported=["RS256", "HS256"],
        claims_supported=[
            "sub", "name", "given_name", "family_name", "preferred_username",
            "email", "email_verified", "phone_number", "phone_number_verified",
            "picture", "locale"
        ]
    )


# =============================================================================
# Authorization Endpoint
# =============================================================================

@router.get(
    "/authorize",
    summary="Authorization Request",
    description="OAuth 2.1 Authorization Endpoint - initiates authorization flow"
)
def authorization_request(
    response_type: str = Query(..., description="Must be 'code'"),
    client_id: str = Query(..., description="Client identifier"),
    redirect_uri: str = Query(..., description="Callback URL"),
    scope: str = Query("profile:read:basic", description="Space-separated scopes"),
    state: Optional[str] = Query(None, description="Client state for CSRF"),
    code_challenge: str = Query(..., description="PKCE code challenge"),
    code_challenge_method: str = Query("S256", description="Must be 'S256'"),
    nonce: Optional[str] = Query(None, description="OIDC nonce"),
    context_type: Optional[str] = Query(None, description="Requested context type"),
    db: Session = Depends(get_db)
):
    """
    OAuth 2.1 Authorization Endpoint.
    
    This endpoint initiates the authorization flow. In a real implementation,
    this would redirect to a login/consent page. For API testing, we return
    the authorization request parameters for processing.
    
    The actual consent flow would be:
    1. User is redirected here
    2. System shows login page (if not authenticated)
    3. System shows consent page (if consent not yet granted)
    4. User approves/denies
    5. System redirects to redirect_uri with code (or error)
    """
    # Validate response_type
    if response_type != "code":
        return _authorization_error_response(
            redirect_uri=redirect_uri,
            error="unsupported_response_type",
            error_description="response_type must be 'code'",
            state=state
        )
    
    # Validate code_challenge_method
    if code_challenge_method != "S256":
        return _authorization_error_response(
            redirect_uri=redirect_uri,
            error="invalid_request",
            error_description="code_challenge_method must be 'S256'",
            state=state
        )
    
    oauth_service = OAuthService(OAuthRepository(db))
    
    try:
        # Validate client and redirect_uri
        client = oauth_service.get_client(client_id)
        oauth_service.validate_redirect_uri(client, redirect_uri)
        
        # Validate scopes
        scope_list = scope.split()
        oauth_service.validate_scopes(client, scope_list)
        
    except InvalidClientError as e:
        return _authorization_error_response(
            redirect_uri=redirect_uri,
            error="unauthorized_client",
            error_description=e.error_description,
            state=state
        )
    except InvalidRequestError as e:
        return _authorization_error_response(
            redirect_uri=redirect_uri,
            error="invalid_request",
            error_description=e.error_description,
            state=state
        )
    except InvalidScopeError as e:
        return _authorization_error_response(
            redirect_uri=redirect_uri,
            error="invalid_scope",
            error_description=e.error_description,
            state=state
        )
    
    # For API testing: Return authorization request info
    # In production, this would render a consent page
    return {
        "message": "Authorization request valid - user consent required",
        "client_id": client_id,
        "client_name": client.client_name,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "context_type": context_type,
        "requires_consent": not client.is_first_party,
        "consent_endpoint": "/oauth/consent"
    }


def _authorization_error_response(
    redirect_uri: str,
    error: str,
    error_description: str,
    state: Optional[str] = None
) -> RedirectResponse:
    """Build authorization error redirect response"""
    from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
    
    params = {
        "error": error,
        "error_description": error_description
    }
    if state:
        params["state"] = state
    
    # Append error params to redirect URI
    parsed = urlparse(redirect_uri)
    query = parse_qs(parsed.query)
    query.update(params)
    new_query = urlencode(query, doseq=True)
    new_url = urlunparse((
        parsed.scheme, parsed.netloc, parsed.path,
        parsed.params, new_query, parsed.fragment
    ))
    
    return RedirectResponse(url=new_url, status_code=status.HTTP_302_FOUND)


# =============================================================================
# Consent Endpoint
# =============================================================================

@router.post(
    "/consent",
    summary="Submit Consent Decision",
    description="Submit user's consent decision for an authorization request"
)
def submit_consent(
    user_id: UUID = Query(..., description="Authenticated user ID"),
    client_id: str = Query(..., description="Client requesting authorization"),
    redirect_uri: str = Query(..., description="Client callback URL"),
    scope: str = Query(..., description="Requested scopes"),
    state: Optional[str] = Query(None, description="Client state"),
    code_challenge: str = Query(..., description="PKCE challenge"),
    code_challenge_method: str = Query("S256", description="PKCE method"),
    approved: bool = Query(..., description="Whether user approved"),
    granted_scopes: Optional[str] = Query(None, description="Approved scopes (subset)"),
    context_profile_id: Optional[UUID] = Query(None, description="Context to bind"),
    nonce: Optional[str] = Query(None, description="OIDC nonce"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Process user consent decision.
    
    If approved, creates authorization code and redirects to client.
    If denied, redirects with access_denied error.
    """
    oauth_service = OAuthService(OAuthRepository(db))
    
    if not approved:
        return _authorization_error_response(
            redirect_uri=redirect_uri,
            error="access_denied",
            error_description="User denied the authorization request",
            state=state
        )
    
    try:
        # Use granted scopes if provided, otherwise use requested scopes
        final_scope = granted_scopes if granted_scopes else scope
        
        # Record consent
        ip_address = request.client.host if request else None
        user_agent = request.headers.get("user-agent") if request else None
        
        oauth_service.record_consent(
            user_id=user_id,
            client_id=client_id,
            granted_scopes=final_scope.split(),
            context_profile_id=context_profile_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Create authorization code
        auth_code = oauth_service.create_authorization_code(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=final_scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            state=state,
            context_profile_id=context_profile_id,
            nonce=nonce
        )
        
        # Redirect with code
        from urllib.parse import urlencode
        params = {"code": auth_code.code}
        if state:
            params["state"] = state
        
        redirect_url = f"{redirect_uri}?{urlencode(params)}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
        
    except OAuthServiceError as e:
        return _authorization_error_response(
            redirect_uri=redirect_uri,
            error=e.error,
            error_description=e.error_description,
            state=state
        )


# =============================================================================
# Token Endpoint
# =============================================================================

@router.post(
    "/token",
    response_model=TokenResponse,
    responses={
        400: {"model": TokenErrorResponse, "description": "Invalid request"},
        401: {"model": TokenErrorResponse, "description": "Invalid client"}
    },
    summary="Token Request",
    description="OAuth 2.1 Token Endpoint - exchange code or refresh token for access token"
)
def token_request(
    grant_type: str = Form(..., description="Grant type"),
    code: Optional[str] = Form(None, description="Authorization code"),
    redirect_uri: Optional[str] = Form(None, description="Redirect URI"),
    code_verifier: Optional[str] = Form(None, description="PKCE verifier"),
    refresh_token: Optional[str] = Form(None, description="Refresh token"),
    client_id: Optional[str] = Form(None, description="Client ID"),
    client_secret: Optional[str] = Form(None, description="Client secret"),
    scope: Optional[str] = Form(None, description="Reduced scope"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """
    OAuth 2.1 Token Endpoint.
    
    Supports:
    - authorization_code: Exchange code for tokens (requires PKCE)
    - refresh_token: Exchange refresh token for new tokens (with rotation)
    
    Client authentication:
    - Public clients: client_id in body, no secret
    - Confidential clients: client_secret_post or client_secret_basic
    """
    oauth_service = OAuthService(OAuthRepository(db))
    
    # Extract client credentials from Authorization header if present
    if authorization and authorization.startswith("Basic "):
        import base64
        try:
            credentials = base64.b64decode(authorization[6:]).decode()
            header_client_id, header_client_secret = credentials.split(":", 1)
            if not client_id:
                client_id = header_client_id
            if not client_secret:
                client_secret = header_client_secret
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "invalid_client", "error_description": "Invalid Authorization header"}
            )
    
    try:
        if grant_type == "authorization_code":
            if not code:
                raise InvalidRequestError("code is required")
            if not redirect_uri:
                raise InvalidRequestError("redirect_uri is required")
            if not code_verifier:
                raise InvalidRequestError("code_verifier is required (PKCE)")
            if not client_id:
                raise InvalidRequestError("client_id is required")
            
            result = oauth_service.exchange_authorization_code(
                code=code,
                client_id=client_id,
                redirect_uri=redirect_uri,
                code_verifier=code_verifier,
                client_secret=client_secret
            )
            
        elif grant_type == "refresh_token":
            if not refresh_token:
                raise InvalidRequestError("refresh_token is required")
            if not client_id:
                raise InvalidRequestError("client_id is required")
            
            result = oauth_service.refresh_access_token(
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                scope=scope
            )
            
        else:
            raise InvalidRequestError(f"Unsupported grant_type: {grant_type}")
        
        return TokenResponse(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
            refresh_token=result.refresh_token,
            scope=result.scope,
            context_profile_id=result.context_profile_id
        )
        
    except InvalidClientError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": e.error, "error_description": e.error_description}
        )
    except (InvalidGrantError, InvalidRequestError, InvalidScopeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.error, "error_description": e.error_description}
        )


# =============================================================================
# Token Introspection Endpoint (RFC 7662)
# =============================================================================

@router.post(
    "/introspect",
    response_model=IntrospectionResponse,
    summary="Token Introspection",
    description="Validate and get metadata about a token (RFC 7662)"
)
def introspect_token(
    token: str = Form(..., description="Token to introspect"),
    token_type_hint: Optional[str] = Form(None, description="Token type hint"),
    client_id: Optional[str] = Form(None, description="Client ID"),
    client_secret: Optional[str] = Form(None, description="Client secret"),
    db: Session = Depends(get_db)
):
    """
    Token Introspection Endpoint.
    
    Resource servers use this to validate tokens and get metadata.
    """
    oauth_service = OAuthService(OAuthRepository(db))
    
    result = oauth_service.introspect_token(token, token_type_hint)
    
    return IntrospectionResponse(
        active=result.active,
        scope=result.scope,
        client_id=result.client_id,
        username=result.username,
        token_type=result.token_type,
        exp=result.exp,
        iat=result.iat,
        sub=result.sub,
        aud=result.aud,
        context_profile_id=result.context_profile_id,
        context_type=result.context_type
    )


# =============================================================================
# Token Revocation Endpoint (RFC 7009)
# =============================================================================

@router.post(
    "/revoke",
    status_code=status.HTTP_200_OK,
    summary="Token Revocation",
    description="Revoke an access or refresh token (RFC 7009)"
)
def revoke_token(
    token: str = Form(..., description="Token to revoke"),
    token_type_hint: Optional[str] = Form(None, description="Token type hint"),
    client_id: Optional[str] = Form(None, description="Client ID"),
    client_secret: Optional[str] = Form(None, description="Client secret"),
    db: Session = Depends(get_db)
):
    """
    Token Revocation Endpoint.
    
    Per RFC 7009, always returns 200 OK (even if token unknown).
    """
    oauth_service = OAuthService(OAuthRepository(db))
    
    oauth_service.revoke_token(token, token_type_hint, client_id)
    
    return Response(status_code=status.HTTP_200_OK)


# =============================================================================
# UserInfo Endpoint (OIDC)
# =============================================================================

@router.get(
    "/userinfo",
    response_model=UserInfoResponse,
    summary="UserInfo",
    description="Get user profile information based on access token scopes"
)
def get_userinfo(
    authorization: str = Header(..., description="Bearer token"),
    db: Session = Depends(get_db)
):
    """
    OIDC UserInfo Endpoint.
    
    Returns user profile claims based on granted scopes.
    Fields are filtered by scope.
    """
    # Extract token from Authorization header
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header"
        )
    
    token = authorization[7:]
    
    oauth_repo = OAuthRepository(db)
    profile_repo = ProfileRepository(db)
    context_repo = ContextRepository(db)
    oauth_service = OAuthService(oauth_repo, profile_repo, context_repo)
    
    # Validate token
    access_token = oauth_repo.get_active_access_token(token)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token"
        )
    
    # Get user profile
    profile = profile_repo.get_by_user_id(access_token.user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    # Get context profile if bound
    context_profile = None
    if access_token.context_profile_id:
        context_profile = context_repo.get_by_id(access_token.context_profile_id)
    
    # Build response based on scopes
    scopes = access_token.get_scopes_list()
    
    response = UserInfoResponse(sub=str(profile.user_id))
    
    # Basic profile claims
    if any(s in scopes for s in ['profile:read:basic', 'profile:read:full', 'openid']):
        # Get identity names for display name
        names = profile_repo.get_profile_names(profile.user_id)
        full_name = None
        given_name = None
        family_name = None
        
        for name in names:
            if not name.is_deprecated:
                if name.name_type.value == 'full_name' and name.name_value:
                    full_name = name.get_name_for_language('en')
                elif name.name_type.value == 'given' and name.name_value:
                    given_name = name.get_name_for_language('en')
                elif name.name_type.value == 'family' and name.name_value:
                    family_name = name.get_name_for_language('en')
        
        if context_profile and context_profile.display_name_override:
            response.name = context_profile.display_name_override
        else:
            response.name = full_name
        
        response.given_name = given_name
        response.family_name = family_name
        response.preferred_username = response.name
        response.locale = profile.preferred_language
        response.account_type = profile.account_type.value
    
    # Email claims
    if any(s in scopes for s in ['profile:read:email', 'profile:read:full', 'email']):
        if context_profile and context_profile.email_override:
            response.email = context_profile.email_override
        else:
            response.email = profile.primary_email
        response.email_verified = True  # TODO: Check auth_users
    
    # Phone claims
    if any(s in scopes for s in ['profile:read:phone', 'profile:read:full', 'phone']):
        if context_profile and context_profile.phone_override:
            response.phone_number = context_profile.phone_override
        else:
            response.phone_number = profile.primary_phone
        response.phone_number_verified = profile.primary_phone is not None
    
    # Context claims
    if context_profile:
        response.context = context_profile.context_type.value
        response.context_name = context_profile.context_name
        if context_profile.bio:
            response.bio = context_profile.bio
    
    return response


# =============================================================================
# Consent Management Endpoints
# =============================================================================

@router.get(
    "/consents",
    response_model=ConsentListResponse,
    summary="List User Consents",
    description="List all active OAuth consents for a user"
)
def list_user_consents(
    user_id: UUID = Query(..., description="User ID"),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """
    List all active consents for a user.
    
    Users can see which applications have access to their data.
    """
    consents = oauth_service.get_user_consents(user_id)
    
    consent_responses = []
    for consent in consents:
        consent_responses.append(ConsentResponse(
            id=consent.id,
            user_id=consent.user_id,
            client_id=consent.client_id,
            client_name=consent.client.client_name if consent.client else "Unknown",
            granted_scopes=consent.granted_scopes,
            context_profile_id=consent.context_profile_id,
            granted_at=consent.granted_at,
            expires_at=consent.expires_at,
            withdrawn_at=consent.withdrawn_at,
            is_active=consent.is_active
        ))
    
    return ConsentListResponse(
        consents=consent_responses,
        total=len(consent_responses)
    )


@router.delete(
    "/consents/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Withdraw Consent",
    description="Withdraw consent for a specific client"
)
def withdraw_consent(
    client_id: str,
    user_id: UUID = Query(..., description="User ID"),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """
    Withdraw consent for a client.
    
    This revokes all tokens and the client will need to re-request authorization.
    Implements GDPR Article 7(3) - right to withdraw consent.
    """
    result = oauth_service.withdraw_consent(user_id, client_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active consent found for this client"
        )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Scope Information Endpoint
# =============================================================================

@router.get(
    "/scopes",
    response_model=ScopeListResponse,
    summary="List Available Scopes",
    description="List all available OAuth scopes"
)
def list_scopes(db: Session = Depends(get_db)):
    """
    List all available OAuth scopes.
    
    Useful for clients to understand what access levels are available.
    """
    oauth_repo = OAuthRepository(db)
    scopes = oauth_repo.list_all_scopes()
    
    scope_responses = []
    for scope in scopes:
        scope_responses.append(ScopeInfo(
            scope_name=scope.scope_name,
            description=scope.description,
            required_context_type=scope.required_context_type,
            is_sensitive=scope.is_sensitive
        ))
    
    return ScopeListResponse(scopes=scope_responses)
