"""
Models Package

SQLAlchemy models for the Identity and Profile Management API.
Defines database entities and their relationships.
"""

from src.models.audit import AuditEventType, AuditLog, AuditOperation
from src.models.auth import AuthUser
from src.models.context import ContextProfile, ContextType
from src.models.oauth import (
    AccessLevel,
    ConsentMethod,
    OAuthAccessToken,
    OAuthAuthorizationCode,
    OAuthClient,
    OAuthConsent,
    OAuthRefreshToken,
    OAuthScope,
    TokenEndpointAuthMethod,
)
from src.models.profile import BaseProfile, IdentityName
from src.models.verification import (
    DocumentType,
    VerificationDocument,
    VerificationStatus,
)

__all__ = [
    "BaseProfile",
    "IdentityName",
    "ContextProfile",
    "ContextType",
    "AuthUser",
    "OAuthScope",
    "OAuthClient",
    "OAuthAuthorizationCode",
    "OAuthAccessToken",
    "OAuthRefreshToken",
    "OAuthConsent",
    "AccessLevel",
    "TokenEndpointAuthMethod",
    "ConsentMethod",
    "AuditLog",
    "AuditOperation",
    "AuditEventType",
    "VerificationDocument",
    "DocumentType",
    "VerificationStatus",
]
