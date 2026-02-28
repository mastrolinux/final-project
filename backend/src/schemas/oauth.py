"""
OAuth 2.1 Schemas

Pydantic models for OAuth 2.1 request/response validation.
Implements OAuth 2.1 specification with PKCE support.
"""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models.context import ContextType


class GrantType(str, Enum):
    """OAuth 2.1 grant types"""

    authorization_code = "authorization_code"
    refresh_token = "refresh_token"


class TokenType(str, Enum):
    """OAuth token types"""

    bearer = "Bearer"


class ErrorCode(str, Enum):
    """OAuth 2.1 error codes (RFC 6749 Section 4.1.2.1)"""

    invalid_request = "invalid_request"
    unauthorized_client = "unauthorized_client"
    access_denied = "access_denied"
    unsupported_response_type = "unsupported_response_type"
    invalid_scope = "invalid_scope"
    server_error = "server_error"
    temporarily_unavailable = "temporarily_unavailable"
    invalid_grant = "invalid_grant"
    invalid_client = "invalid_client"
    unsupported_grant_type = "unsupported_grant_type"


#
# Authorization Request/Response Schemas
#


class AuthorizationRequest(BaseModel):
    """OAuth 2.1 Authorization Request with mandatory PKCE."""

    response_type: str = Field(..., description="Must be 'code' for Authorization Code Flow")
    client_id: str = Field(..., min_length=1, max_length=64, description="Client identifier")
    redirect_uri: str = Field(..., description="Callback URL (must match registered URI exactly)")
    scope: str = Field(
        default="profile:read:basic", description="Space-separated list of requested scopes"
    )
    state: str | None = Field(
        default=None, max_length=256, description="Client state parameter for CSRF protection"
    )
    code_challenge: str = Field(
        ...,
        min_length=43,
        max_length=128,
        description="PKCE code challenge (base64url-encoded SHA256 of verifier)",
    )
    code_challenge_method: str = Field(
        default="S256", description="PKCE challenge method (must be 'S256')"
    )
    nonce: str | None = Field(
        default=None, max_length=256, description="OIDC nonce for ID token binding"
    )
    context_type: ContextType | None = Field(
        default=None, description="Requested context type for context-aware authorization"
    )

    @field_validator("response_type")
    @classmethod
    def validate_response_type(cls, v):
        """Validate response_type is 'code'"""
        if v != "code":
            raise ValueError("response_type must be 'code'")
        return v

    @field_validator("code_challenge_method")
    @classmethod
    def validate_challenge_method(cls, v):
        """Validate code_challenge_method is 'S256' (plain not allowed in OAuth 2.1)"""
        if v != "S256":
            raise ValueError("code_challenge_method must be 'S256'")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "response_type": "code",
                    "client_id": "linkedin-demo",
                    "redirect_uri": "https://linkedin-demo.example.com/callback",
                    "scope": "openid profile:read:basic profile:read:email",
                    "state": "abc123xyz",
                    "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                    "code_challenge_method": "S256",
                    "context_type": "professional",
                }
            ]
        }
    )


class AuthorizationResponse(BaseModel):
    """OAuth 2.1 Authorization Response with authorization code."""

    code: str = Field(..., description="Authorization code (valid for 10 minutes)")
    state: str | None = Field(
        default=None, description="Client state parameter (returned unchanged)"
    )

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"code": "SplxlOBeZQQYbYS6WxSbIA", "state": "abc123xyz"}]}
    )


class AuthorizationErrorResponse(BaseModel):
    """OAuth 2.1 Authorization Error Response."""

    error: ErrorCode
    error_description: str | None = None
    error_uri: str | None = None
    state: str | None = None


#
# Token Request/Response Schemas
#


class TokenRequest(BaseModel):
    """OAuth 2.1 Token Request (authorization_code or refresh_token grant)."""

    grant_type: GrantType = Field(
        ..., description="Grant type: 'authorization_code' or 'refresh_token'"
    )

    code: str | None = Field(
        default=None, description="Authorization code (required for authorization_code grant)"
    )
    redirect_uri: str | None = Field(
        default=None, description="Redirect URI (required for authorization_code grant)"
    )
    code_verifier: str | None = Field(
        default=None,
        min_length=43,
        max_length=128,
        description="PKCE code verifier (required for authorization_code grant)",
    )

    refresh_token: str | None = Field(
        default=None, description="Refresh token (required for refresh_token grant)"
    )

    client_id: str | None = Field(
        default=None, description="Client ID (required for public clients)"
    )
    client_secret: str | None = Field(
        default=None, description="Client secret (required for confidential clients)"
    )

    scope: str | None = Field(
        default=None, description="Reduced scope (must be subset of original)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "grant_type": "authorization_code",
                    "code": "SplxlOBeZQQYbYS6WxSbIA",
                    "redirect_uri": "https://linkedin-demo.example.com/callback",
                    "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
                    "client_id": "linkedin-demo",
                }
            ]
        }
    )


class TokenResponse(BaseModel):
    """OAuth 2.1 Token Response."""

    access_token: str = Field(..., description="Access token for API authorization")
    token_type: TokenType = Field(
        default=TokenType.bearer, description="Token type (always 'Bearer')"
    )
    expires_in: int = Field(..., description="Access token lifetime in seconds")
    refresh_token: str | None = Field(
        default=None, description="Refresh token (if offline_access scope granted)"
    )
    scope: str = Field(..., description="Granted scopes (may differ from requested)")

    id_token: str | None = Field(default=None, description="ID token (if openid scope included)")

    context_profile_id: UUID | None = Field(
        default=None, description="Context profile ID (if context-specific authorization)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA",
                    "scope": "openid profile:read:basic profile:read:email",
                    "context_profile_id": "20000000-0000-0000-0000-000000000001",
                }
            ]
        }
    )


class TokenErrorResponse(BaseModel):
    """OAuth 2.1 Token Error Response."""

    error: ErrorCode
    error_description: str | None = None
    error_uri: str | None = None


#
# Token Introspection Schemas (RFC 7662)
#


class IntrospectionRequest(BaseModel):
    """Token Introspection Request (RFC 7662)."""

    token: str = Field(..., description="Token to introspect")
    token_type_hint: str | None = Field(
        default=None, description="Hint about token type: 'access_token' or 'refresh_token'"
    )


class IntrospectionResponse(BaseModel):
    """Token Introspection Response (RFC 7662)."""

    active: bool = Field(..., description="Whether token is currently active")

    scope: str | None = None
    client_id: str | None = None
    username: str | None = None
    token_type: str | None = None
    exp: int | None = Field(default=None, description="Expiration timestamp (Unix epoch)")
    iat: int | None = Field(default=None, description="Issued at timestamp (Unix epoch)")
    nbf: int | None = Field(default=None, description="Not before timestamp (Unix epoch)")
    sub: str | None = Field(default=None, description="Subject (user ID)")
    aud: str | None = Field(default=None, description="Audience (client ID)")
    iss: str | None = Field(default=None, description="Issuer URL")
    jti: str | None = Field(default=None, description="Token identifier")

    context_profile_id: UUID | None = None
    context_type: ContextType | None = None
    context_verified: bool | None = Field(
        default=None,
        description=(
            "Whether the bound context has passed identity verification. "
            "None when no context is bound or the context type does not "
            "require verification."
        ),
    )


#
# Token Revocation Schemas (RFC 7009)
#


class RevocationRequest(BaseModel):
    """Token Revocation Request (RFC 7009)."""

    token: str = Field(..., description="Token to revoke")
    token_type_hint: str | None = Field(
        default=None, description="Hint about token type: 'access_token' or 'refresh_token'"
    )

    client_id: str | None = None
    client_secret: str | None = None


#
# UserInfo Schemas (OIDC Core)
#


class UserInfoResponse(BaseModel):
    """OIDC UserInfo Response with context-awareness extensions."""

    sub: str = Field(..., description="Subject identifier (user_id)")
    name: str | None = Field(default=None, description="Full name")
    given_name: str | None = None
    family_name: str | None = None
    preferred_username: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    phone_number: str | None = None
    phone_number_verified: bool | None = None
    picture: str | None = None
    locale: str | None = None

    context: str | None = Field(
        default=None, description="Current context type (professional, social, etc.)"
    )
    context_name: str | None = Field(default=None, description="Context name")
    account_type: str | None = Field(default=None, description="Account verification level")
    bio: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "sub": "00000000-0000-0000-0000-000000000001",
                    "name": "Dr. Sarah Chen, MD, PhD",
                    "given_name": "Sarah",
                    "family_name": "Chen",
                    "preferred_username": "Dr. Sarah Chen",
                    "email": "s.chen@hospital.org",
                    "email_verified": True,
                    "locale": "en",
                    "context": "professional",
                    "context_name": "Hospital Network",
                    "account_type": "verified",
                    "bio": "Board-certified psychiatrist",
                }
            ]
        }
    )


#
# OAuth Client Schemas
#


class OAuthClientCreate(BaseModel):
    """Schema for registering a new OAuth client"""

    client_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern="^[a-zA-Z0-9_-]+$",
        description="Unique client identifier",
    )
    client_name: str = Field(
        ..., min_length=1, max_length=255, description="Display name for consent screen"
    )
    client_description: str | None = None
    client_uri: str | None = None
    logo_uri: str | None = None
    redirect_uris: list[str] = Field(
        ..., min_length=1, description="Allowed redirect URIs (exact match required)"
    )
    allowed_scopes: list[str] = Field(
        default=["profile:read:basic"], description="Scopes this client can request"
    )
    default_context_type: ContextType | None = None
    is_confidential: bool = Field(
        default=False, description="Whether client can securely store secrets"
    )
    is_first_party: bool = Field(default=False, description="First-party apps can skip consent")
    client_secret: str | None = Field(
        default=None, description="Client secret (required for confidential clients)"
    )


class OAuthClientUpdate(BaseModel):
    """Schema for updating an OAuth client"""

    client_name: str | None = Field(
        default=None, min_length=1, max_length=255, description="Display name for consent screen"
    )
    client_description: str | None = None
    client_uri: str | None = None
    logo_uri: str | None = None
    redirect_uris: list[str] | None = Field(
        default=None, min_length=1, description="Allowed redirect URIs"
    )
    allowed_scopes: list[str] | None = Field(
        default=None, description="Scopes this client can request"
    )
    default_context_type: ContextType | None = None
    is_active: bool | None = None
    is_first_party: bool | None = None

    client_secret: str | None = Field(
        default=None, description="New client secret (only for confidential clients)"
    )


class OAuthClientResponse(BaseModel):
    """Schema for OAuth client response (does NOT include secret)"""

    client_id: str
    client_name: str
    client_description: str | None = None
    client_uri: str | None = None
    logo_uri: str | None = None
    redirect_uris: list[str]
    allowed_scopes: list[str]
    default_context_type: ContextType | None = None
    is_confidential: bool
    is_active: bool
    is_first_party: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OAuthClientCreateResponse(BaseModel):
    """Schema for OAuth client creation response (secret shown only once)."""

    client_id: str
    client_name: str
    client_description: str | None = None
    client_uri: str | None = None
    logo_uri: str | None = None
    redirect_uris: list[str]
    allowed_scopes: list[str]
    default_context_type: ContextType | None = None
    is_confidential: bool
    is_active: bool
    is_first_party: bool
    created_at: datetime

    client_secret: str | None = Field(
        default=None, description="Client secret (shown only once, store securely)"
    )

    model_config = ConfigDict(from_attributes=True)


class OAuthClientListResponse(BaseModel):
    """Schema for paginated list of OAuth clients"""

    clients: list[OAuthClientResponse]
    total: int
    page: int = 1
    page_size: int = 20


#
# Consent Schemas
#


class ConsentRequest(BaseModel):
    """Schema for consent decision from user."""

    client_id: str
    approved: bool = Field(..., description="Whether user approved the consent")
    granted_scopes: list[str] | None = Field(
        default=None, description="Scopes user approved (may be subset of requested)"
    )
    context_profile_id: UUID | None = Field(
        default=None, description="Context profile to use for this authorization"
    )


class ConsentResponse(BaseModel):
    """Schema for consent record response"""

    id: UUID
    user_id: UUID
    client_id: str
    client_name: str
    granted_scopes: list[str]
    context_profile_id: UUID | None = None
    granted_at: datetime
    expires_at: datetime | None = None
    withdrawn_at: datetime | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ConsentListResponse(BaseModel):
    """Schema for list of user consents"""

    consents: list[ConsentResponse]
    total: int


#
# Authorization Consent Flow Schemas (Frontend API Contract)
#


class ConsentClientInfo(BaseModel):
    """Client information for consent screen display."""

    client_id: str = Field(..., description="Client identifier")
    client_name: str = Field(..., description="Human-readable client name")
    client_description: str | None = Field(default=None, description="Client description")
    client_uri: str | None = Field(default=None, description="Client homepage URL")
    logo_uri: str | None = Field(default=None, description="Client logo URL for consent screen")
    is_first_party: bool = Field(
        ..., description="Whether client is operated by the identity provider"
    )


class ConsentScopeInfo(BaseModel):
    """Scope information for consent screen display."""

    scope_name: str = Field(..., description="Scope identifier")
    description: str = Field(..., description="Human-readable scope description")
    is_sensitive: bool = Field(..., description="Whether scope grants access to sensitive data")
    required_context_type: ContextType | None = Field(
        default=None, description="Context type required for this scope"
    )

    model_config = ConfigDict(from_attributes=True)


class ConsentRequestInfo(BaseModel):
    """Authorization request parameters echoed back for consent flow."""

    client_id: str = Field(..., description="Client identifier")
    response_type: str = Field(..., description="OAuth response type")
    redirect_uri: str = Field(..., description="Client callback URL")
    scope: str = Field(..., description="Space-separated requested scopes")
    state: str | None = Field(default=None, description="Client state for CSRF")
    code_challenge: str = Field(..., description="PKCE code challenge")
    code_challenge_method: str = Field(..., description="PKCE challenge method")
    nonce: str | None = Field(default=None, description="OIDC nonce")
    context_type: str | None = Field(default=None, description="Requested context type")


class AuthorizationConsentResponse(BaseModel):
    """Response for authorization consent screen rendering."""

    client: ConsentClientInfo = Field(..., description="Client information for display")
    scopes: list[ConsentScopeInfo] = Field(..., description="Requested scopes with descriptions")
    request: ConsentRequestInfo = Field(..., description="Authorization request parameters")
    requires_consent: bool = Field(..., description="Whether explicit consent is required")


class ConsentDecisionRequestBody(BaseModel):
    """Request body for consent decision submission."""

    client_id: str = Field(..., description="Client identifier")
    scope: str = Field(..., description="Requested scopes")
    state: str | None = Field(default=None, description="Client state")
    redirect_uri: str = Field(..., description="Client callback URL")
    response_type: str = Field(..., description="OAuth response type")
    code_challenge: str = Field(..., description="PKCE code challenge")
    code_challenge_method: str = Field(default="S256", description="PKCE challenge method")
    nonce: str | None = Field(default=None, description="OIDC nonce")
    decision: Literal["allow", "deny"] = Field(..., description="User's consent decision")
    context_id: UUID | None = Field(
        default=None, description="Context profile to bind to authorization"
    )
    remember: bool = Field(
        default=True, description="Whether to persist consent for future requests"
    )


class ConsentDecisionResponseBody(BaseModel):
    """Response after consent decision processing."""

    redirect_to: str = Field(..., description="URL to redirect user to after consent")


#
# OAuth Discovery Schemas (RFC 8414)
#


class OAuthServerMetadata(BaseModel):
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str | None = None
    introspection_endpoint: str | None = None
    revocation_endpoint: str | None = None
    jwks_uri: str | None = None

    scopes_supported: list[str]
    response_types_supported: list[str] = ["code"]
    response_modes_supported: list[str] = ["query"]
    grant_types_supported: list[str] = ["authorization_code", "refresh_token"]
    token_endpoint_auth_methods_supported: list[str] = [
        "none",
        "client_secret_post",
        "client_secret_basic",
    ]
    code_challenge_methods_supported: list[str] = ["S256"]

    subject_types_supported: list[str] = ["public"]
    id_token_signing_alg_values_supported: list[str] = ["RS256", "HS256"]
    claims_supported: list[str] = [
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
    ]


#
# Scope Information Schemas
#


class ScopeInfo(BaseModel):
    """Schema for scope information display"""

    scope_name: str
    description: str
    required_context_type: ContextType | None = None
    is_sensitive: bool

    model_config = ConfigDict(from_attributes=True)


class ScopeListResponse(BaseModel):
    """Schema for list of available scopes"""

    scopes: list[ScopeInfo]
