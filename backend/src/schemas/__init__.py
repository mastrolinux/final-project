"""
Schemas Package

Pydantic models for request/response validation.
"""

from src.schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse
from src.schemas.context import (
    ContextProfileCreate,
    ContextProfileUpdate,
    ContextProfileResponse,
    ResolvedProfileResponse
)
from src.schemas.audit import (
    AuditLogEntry,
    AuditTrailResponse,
    AuditIntegrityResponse
)
from src.schemas.oauth import (
    AuthorizationRequest,
    AuthorizationResponse,
    TokenRequest,
    TokenResponse,
    IntrospectionRequest,
    IntrospectionResponse,
    RevocationRequest,
    UserInfoResponse,
    OAuthClientCreate,
    OAuthClientResponse,
    ConsentRequest,
    ConsentResponse,
    OAuthServerMetadata,
    ScopeInfo
)

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
