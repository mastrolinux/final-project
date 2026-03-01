"""
OAuth 2.1 Endpoints

REST API endpoints for OAuth 2.1 authorization server.
Implements Authorization Code Flow with mandatory PKCE.
"""

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.api.dependencies.auth import get_current_user, get_current_user_optional
from src.core.database import get_db
from src.models.auth import AuthUser
from src.repositories.audit_repository import AuditRepository
from src.repositories.context_repository import ContextRepository
from src.repositories.oauth_repository import OAuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.schemas.oauth import (
    AuthorizationConsentResponse,
    ConsentClientInfo,
    ConsentDecisionRequestBody,
    ConsentDecisionResponseBody,
    ConsentListResponse,
    ConsentRequestInfo,
    ConsentResponse,
    ConsentScopeInfo,
    IntrospectionResponse,
    OAuthServerMetadata,
    ScopeInfo,
    ScopeListResponse,
    TokenErrorResponse,
    TokenResponse,
    UserInfoResponse,
)
from src.services.audit_service import AuditService
from src.services.oauth_service import (
    InvalidClientError,
    InvalidGrantError,
    InvalidRequestError,
    InvalidScopeError,
    OAuthService,
    OAuthServiceError,
)

router = APIRouter()


def get_oauth_service(db: Session = Depends(get_db)) -> OAuthService:
    """Dependency to get OAuthService instance with audit logging."""
    oauth_repo = OAuthRepository(db)
    profile_repo = ProfileRepository(db)
    context_repo = ContextRepository(db)
    audit_repo = AuditRepository(db)
    audit_service = AuditService(audit_repo)
    return OAuthService(oauth_repo, profile_repo, context_repo, audit_service=audit_service)


#
# OAuth 2.1 Discovery Endpoint
#


@router.get(
    "/.well-known/oauth-authorization-server",
    response_model=OAuthServerMetadata,
    summary="OAuth Server Metadata",
    description="Returns OAuth 2.0 Authorization Server Metadata (RFC 8414)",
)
def get_oauth_metadata(request: Request):
    """Return OAuth server metadata for client auto-configuration."""
    base_url = str(request.base_url).rstrip("/")

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
            "offline_access",
        ],
        response_types_supported=["code"],
        response_modes_supported=["query"],
        grant_types_supported=["authorization_code", "refresh_token"],
        token_endpoint_auth_methods_supported=["none", "client_secret_post", "client_secret_basic"],
        code_challenge_methods_supported=["S256"],
        subject_types_supported=["public"],
        id_token_signing_alg_values_supported=["RS256", "HS256"],
        claims_supported=[
            "sub",
            "name",
            "given_name",
            "family_name",
            "preferred_username",
            "email",
            "email_verified",
            "phone_number",
            "phone_number_verified",
            "picture",
            "locale",
        ],
    )


#
# Authorization Endpoint
#


@router.get(
    "/authorize",
    summary="Authorization Request",
    description="OAuth 2.1 Authorization Endpoint - initiates authorization flow",
    response_model=AuthorizationConsentResponse,
)
async def authorization_request(
    request: Request,
    response_type: str = Query(..., description="Must be 'code'"),
    client_id: str = Query(..., description="Client identifier"),
    redirect_uri: str = Query(..., description="Callback URL"),
    scope: str = Query("profile:read:basic", description="Space-separated scopes"),
    state: str | None = Query(None, description="Client state for CSRF"),
    code_challenge: str = Query(..., description="PKCE code challenge"),
    code_challenge_method: str = Query("S256", description="Must be 'S256'"),
    nonce: str | None = Query(None, description="OIDC nonce"),
    context_type: str | None = Query(None, description="Requested context type"),
    current_user: AuthUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Return authorization request details for the frontend consent screen."""
    # SPA sends Accept: application/json; return JSON errors instead of 302
    # redirects to avoid cross-origin CORS failures.
    accept_header = request.headers.get("accept", "")
    wants_json = "application/json" in accept_header

    if response_type != "code":
        return _authorization_error_response(
            redirect_uri=redirect_uri,
            error="unsupported_response_type",
            error_description="response_type must be 'code'",
            state=state,
            accept_json=wants_json,
        )

    if code_challenge_method != "S256":
        return _authorization_error_response(
            redirect_uri=redirect_uri,
            error="invalid_request",
            error_description="code_challenge_method must be 'S256'",
            state=state,
            accept_json=wants_json,
        )

    oauth_service = OAuthService(OAuthRepository(db))

    try:
        client = oauth_service.get_client(client_id)
        oauth_service.validate_redirect_uri(client, redirect_uri)
        scope_list = scope.split()
        oauth_service.validate_scopes(client, scope_list)
        scope_details = oauth_service.get_scope_details(scope_list)

    except InvalidClientError as e:
        return _authorization_error_response(
            redirect_uri=redirect_uri,
            error="unauthorized_client",
            error_description=e.error_description,
            state=state,
            accept_json=wants_json,
        )
    except InvalidRequestError as e:
        return _authorization_error_response(
            redirect_uri=redirect_uri,
            error="invalid_request",
            error_description=e.error_description,
            state=state,
            accept_json=wants_json,
        )
    except InvalidScopeError as e:
        return _authorization_error_response(
            redirect_uri=redirect_uri,
            error="invalid_scope",
            error_description=e.error_description,
            state=state,
            accept_json=wants_json,
        )

    client_info = ConsentClientInfo(
        client_id=client.client_id,
        client_name=client.client_name,
        client_description=client.client_description,
        client_uri=client.client_uri,
        logo_uri=client.logo_uri,
        is_first_party=client.is_first_party,
    )

    scope_infos = [
        ConsentScopeInfo(
            scope_name=s.scope_name,
            description=s.description,
            is_sensitive=s.is_sensitive,
            required_context_type=s.required_context_type,
        )
        for s in scope_details
    ]

    request_info = ConsentRequestInfo(
        client_id=client_id,
        response_type=response_type,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        nonce=nonce,
        context_type=context_type,
    )

    # First-party clients skip consent; returning users with remembered
    # consent covering all requested scopes also skip.
    requires_consent = True
    if client.is_first_party:
        requires_consent = False
    elif current_user:
        scope_list_for_check = scope.split()
        has_consent = oauth_service.check_consent(
            user_id=current_user.user_id, client_id=client_id, required_scopes=scope_list_for_check
        )
        if has_consent:
            requires_consent = False

    return AuthorizationConsentResponse(
        client=client_info,
        scopes=scope_infos,
        request=request_info,
        requires_consent=requires_consent,
    )


def _authorization_error_response(
    redirect_uri: str,
    error: str,
    error_description: str,
    state: str | None = None,
    accept_json: bool = False,
) -> Response:
    """Return JSON error for SPA clients, or standard OAuth 302 redirect."""
    if accept_json:
        body = {"error": error, "error_description": error_description}
        if state:
            body["state"] = state
        return JSONResponse(content=body, status_code=status.HTTP_400_BAD_REQUEST)

    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    params = {"error": error, "error_description": error_description}
    if state:
        params["state"] = state

    parsed = urlparse(redirect_uri)
    query = parse_qs(parsed.query)
    query.update(params)
    new_query = urlencode(query, doseq=True)
    new_url = urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    )

    return RedirectResponse(url=new_url, status_code=status.HTTP_302_FOUND)


#
# Consent Endpoint
#


@router.post(
    "/consent",
    summary="Submit Consent Decision",
    description="Submit user's consent decision for an authorization request",
    response_model=ConsentDecisionResponseBody,
)
async def submit_consent(
    consent_data: ConsentDecisionRequestBody,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service),
    db: Session = Depends(get_db),
):
    """Process user consent decision and return redirect URL with authorization code or error."""

    if consent_data.decision == "deny":
        from urllib.parse import urlencode

        params = {
            "error": "access_denied",
            "error_description": "User denied the authorization request",
        }
        if consent_data.state:
            params["state"] = consent_data.state
        redirect_url = f"{consent_data.redirect_uri}?{urlencode(params)}"
        return ConsentDecisionResponseBody(redirect_to=redirect_url)

    try:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Only persist consent when user opted to remember the decision
        if consent_data.remember:
            oauth_service.record_consent(
                user_id=current_user.user_id,
                client_id=consent_data.client_id,
                granted_scopes=consent_data.scope.split(),
                context_profile_id=consent_data.context_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        auth_code = oauth_service.create_authorization_code(
            client_id=consent_data.client_id,
            user_id=current_user.user_id,
            redirect_uri=consent_data.redirect_uri,
            scope=consent_data.scope,
            code_challenge=consent_data.code_challenge,
            code_challenge_method=consent_data.code_challenge_method,
            state=consent_data.state,
            context_profile_id=consent_data.context_id,
            nonce=consent_data.nonce,
        )

        from urllib.parse import urlencode

        params = {"code": auth_code.code}
        if consent_data.state:
            params["state"] = consent_data.state

        redirect_url = f"{consent_data.redirect_uri}?{urlencode(params)}"
        return ConsentDecisionResponseBody(redirect_to=redirect_url)

    except OAuthServiceError as e:
        from urllib.parse import urlencode

        params = {"error": e.error, "error_description": e.error_description}
        if consent_data.state:
            params["state"] = consent_data.state
        redirect_url = f"{consent_data.redirect_uri}?{urlencode(params)}"
        return ConsentDecisionResponseBody(redirect_to=redirect_url)


#
# Token Endpoint
#


@router.post(
    "/token",
    response_model=TokenResponse,
    responses={
        400: {"model": TokenErrorResponse, "description": "Invalid request"},
        401: {"model": TokenErrorResponse, "description": "Invalid client"},
    },
    summary="Token Request",
    description="OAuth 2.1 Token Endpoint - exchange code or refresh token for access token",
)
def token_request(
    grant_type: str = Form(..., description="Grant type"),
    code: str | None = Form(None, description="Authorization code"),
    redirect_uri: str | None = Form(None, description="Redirect URI"),
    code_verifier: str | None = Form(None, description="PKCE verifier"),
    refresh_token: str | None = Form(None, description="Refresh token"),
    client_id: str | None = Form(None, description="Client ID"),
    client_secret: str | None = Form(None, description="Client secret"),
    scope: str | None = Form(None, description="Reduced scope"),
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    """Exchange authorization code or refresh token for access tokens."""
    audit_repo = AuditRepository(db)
    audit_svc = AuditService(audit_repo)
    oauth_service = OAuthService(OAuthRepository(db), audit_service=audit_svc)

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
                detail={
                    "error": "invalid_client",
                    "error_description": "Invalid Authorization header",
                },
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
                client_secret=client_secret,
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
                scope=scope,
            )

        else:
            raise InvalidRequestError(f"Unsupported grant_type: {grant_type}")

        return TokenResponse(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
            refresh_token=result.refresh_token,
            scope=result.scope,
            context_profile_id=result.context_profile_id,
        )

    except InvalidClientError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": e.error, "error_description": e.error_description},
        )
    except (InvalidGrantError, InvalidRequestError, InvalidScopeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.error, "error_description": e.error_description},
        )


#
# Token Introspection Endpoint (RFC 7662)
#


@router.post(
    "/introspect",
    response_model=IntrospectionResponse,
    summary="Token Introspection",
    description="Validate and get metadata about a token (RFC 7662)",
)
def introspect_token(
    token: str = Form(..., description="Token to introspect"),
    token_type_hint: str | None = Form(None, description="Token type hint"),
    client_id: str | None = Form(None, description="Client ID"),
    client_secret: str | None = Form(None, description="Client secret"),
    db: Session = Depends(get_db),
):
    """Validate token and return metadata for resource servers."""
    oauth_service = OAuthService(OAuthRepository(db), context_repo=ContextRepository(db))

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
        context_type=result.context_type,
        context_verified=result.context_verified,
    )


#
# Token Revocation Endpoint (RFC 7009)
#


@router.post(
    "/revoke",
    status_code=status.HTTP_200_OK,
    summary="Token Revocation",
    description="Revoke an access or refresh token (RFC 7009)",
)
def revoke_token(
    token: str = Form(..., description="Token to revoke"),
    token_type_hint: str | None = Form(None, description="Token type hint"),
    client_id: str | None = Form(None, description="Client ID"),
    client_secret: str | None = Form(None, description="Client secret"),
    db: Session = Depends(get_db),
):
    """Revoke a token. Per RFC 7009, always returns 200 OK."""
    audit_repo = AuditRepository(db)
    audit_svc = AuditService(audit_repo)
    oauth_service = OAuthService(OAuthRepository(db), audit_service=audit_svc)

    oauth_service.revoke_token(token, token_type_hint, client_id)

    return Response(status_code=status.HTTP_200_OK)


#
# UserInfo Endpoint (OIDC)
#


@router.get(
    "/userinfo",
    response_model=UserInfoResponse,
    summary="UserInfo",
    description="Get user profile information based on access token scopes",
)
def get_userinfo(
    authorization: str = Header(..., description="Bearer token"), db: Session = Depends(get_db)
):
    """Return user profile claims filtered by granted scopes."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header"
        )

    token = authorization[7:]

    oauth_repo = OAuthRepository(db)
    profile_repo = ProfileRepository(db)
    context_repo = ContextRepository(db)

    access_token = oauth_repo.get_active_access_token(token)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token"
        )

    profile = profile_repo.get_profile_by_id(access_token.user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")

    context_profile = None
    if access_token.context_profile_id:
        context_profile = context_repo.get_context_profile_by_id(access_token.context_profile_id)

    if (
        context_profile
        and context_profile.requires_verification
        and not context_profile.is_identity_verified
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "context_not_verified",
                "message": "Context requires identity verification before use",
                "details": {
                    "context_id": str(access_token.context_profile_id),
                    "verification_status": (
                        context_profile.verification_status.value
                        if context_profile.verification_status
                        else "none"
                    ),
                },
            },
        )

    scopes = access_token.get_scopes_list()

    response = UserInfoResponse(sub=str(profile.user_id))

    if any(s in scopes for s in ["profile:read:basic", "profile:read:full", "openid"]):
        names = profile_repo.get_identity_names(profile.user_id)
        full_name = None
        given_name = None
        family_name = None

        for name in names:
            if not name.is_deprecated:
                if name.name_type.value == "full_name" and name.name_value:
                    full_name = name.get_name_for_language("en")
                elif name.name_type.value == "given" and name.name_value:
                    given_name = name.get_name_for_language("en")
                elif name.name_type.value == "family" and name.name_value:
                    family_name = name.get_name_for_language("en")

        if context_profile and context_profile.display_name_override:
            response.name = context_profile.display_name_override
        else:
            response.name = full_name

        response.given_name = given_name
        response.family_name = family_name
        response.preferred_username = response.name
        response.locale = profile.preferred_language
        response.account_type = profile.account_type.value

    if any(s in scopes for s in ["profile:read:email", "profile:read:full", "email"]):
        if context_profile and context_profile.email_override:
            response.email = context_profile.email_override
        else:
            response.email = profile.primary_email
        response.email_verified = True  # TODO: Check auth_users

    if any(s in scopes for s in ["profile:read:phone", "profile:read:full", "phone"]):
        if context_profile and context_profile.phone_override:
            response.phone_number = context_profile.phone_override
        else:
            response.phone_number = profile.primary_phone
        response.phone_number_verified = profile.primary_phone is not None

    if context_profile:
        response.context = context_profile.context_type.value
        response.context_name = context_profile.context_name
        if context_profile.bio:
            response.bio = context_profile.bio

    return response


#
# Consent Management Endpoints
#


@router.get(
    "/consents",
    response_model=ConsentListResponse,
    summary="List User Consents",
    description="List all active OAuth consents for a user",
)
def list_user_consents(
    user_id: UUID = Query(..., description="User ID"),
    context_id: UUID | None = Query(None, description="Filter by context profile ID"),
    oauth_service: OAuthService = Depends(get_oauth_service),
):
    """List all active OAuth consents for a user."""
    consents = oauth_service.get_user_consents(user_id, context_id)

    consent_responses = []
    for consent in consents:
        consent_responses.append(
            ConsentResponse(
                id=consent.id,
                user_id=consent.user_id,
                client_id=consent.client_id,
                client_name=consent.client.client_name if consent.client else "Unknown",
                granted_scopes=consent.granted_scopes,
                context_profile_id=consent.context_profile_id,
                granted_at=consent.granted_at,
                expires_at=consent.expires_at,
                withdrawn_at=consent.withdrawn_at,
                is_active=consent.is_active,
            )
        )

    return ConsentListResponse(consents=consent_responses, total=len(consent_responses))


@router.delete(
    "/consents/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Withdraw Consent",
    description="Withdraw consent for a specific client",
)
def withdraw_consent(
    client_id: str,
    user_id: UUID = Query(..., description="User ID"),
    oauth_service: OAuthService = Depends(get_oauth_service),
):
    """Withdraw consent and revoke all tokens for a client (GDPR Art. 7(3))."""
    result = oauth_service.withdraw_consent(user_id, client_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active consent found for this client"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


#
# Scope Information Endpoint
#


@router.get(
    "/scopes",
    response_model=ScopeListResponse,
    summary="List Available Scopes",
    description="List all available OAuth scopes",
)
def list_scopes(db: Session = Depends(get_db)):
    """List all available OAuth scopes."""
    oauth_repo = OAuthRepository(db)
    scopes = oauth_repo.list_all_scopes()

    scope_responses = []
    for scope in scopes:
        scope_responses.append(
            ScopeInfo(
                scope_name=scope.scope_name,
                description=scope.description,
                required_context_type=scope.required_context_type,
                is_sensitive=scope.is_sensitive,
            )
        )

    return ScopeListResponse(scopes=scope_responses)
