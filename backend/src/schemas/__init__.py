"""
Schemas Package

Pydantic models for request/response validation.
"""

from src.schemas.audit import AuditIntegrityResponse, AuditLogEntry, AuditTrailResponse
from src.schemas.context import (
    ContextProfileCreate,
    ContextProfileResponse,
    ContextProfileUpdate,
    ResolvedProfileResponse,
)
from src.schemas.oauth import (
    AuthorizationRequest,
    AuthorizationResponse,
    ConsentRequest,
    ConsentResponse,
    IntrospectionRequest,
    IntrospectionResponse,
    OAuthClientCreate,
    OAuthClientResponse,
    OAuthServerMetadata,
    RevocationRequest,
    ScopeInfo,
    TokenRequest,
    TokenResponse,
    UserInfoResponse,
)
from src.schemas.profile import ProfileCreate, ProfileResponse, ProfileUpdate

__all__ = [
    # Profile schemas
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileResponse",
    # Context schemas
    "ContextProfileCreate",
    "ContextProfileUpdate",
    "ContextProfileResponse",
    "ResolvedProfileResponse",
    # OAuth schemas
    "AuthorizationRequest",
    "AuthorizationResponse",
    "TokenRequest",
    "TokenResponse",
    "IntrospectionRequest",
    "IntrospectionResponse",
    "RevocationRequest",
    "UserInfoResponse",
    "OAuthClientCreate",
    "OAuthClientResponse",
    "ConsentRequest",
    "ConsentResponse",
    "OAuthServerMetadata",
    "ScopeInfo",
    # Audit schemas
    "AuditLogEntry",
    "AuditTrailResponse",
    "AuditIntegrityResponse",
]
