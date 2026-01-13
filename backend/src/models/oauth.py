"""
OAuth 2.1 Models

SQLAlchemy models for OAuth 2.1 authorization server.
Implements OAuth 2.1 draft specification with mandatory PKCE,
refresh token rotation, and context-aware token binding.
"""

from datetime import datetime, timezone
from typing import Any, List, Optional
import uuid as uuid_pkg
import enum
import json
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey,
    Enum as SQLEnum, Text, Index, TypeDecorator
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, INET
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship

from src.core.database import Base
from src.models.profile import UUID, TimestampMixin, SoftDeleteMixin
from src.models.context import ContextType


class TextArray(TypeDecorator):
    """
    Platform-independent TEXT[] type.
    
    Uses PostgreSQL's ARRAY(Text) when available, otherwise uses JSON for SQLite.
    This allows tests to run with SQLite while production uses PostgreSQL.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_ARRAY(Text))
        else:
            return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            # PostgreSQL expects a list directly for ARRAY type
            return value
        else:
            # SQLite: store as JSON array
            return json.dumps(value) if isinstance(value, list) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            # PostgreSQL returns list directly
            return value
        else:
            # SQLite: parse JSON array
            if isinstance(value, str):
                return json.loads(value)
            return value


class InetType(TypeDecorator):
    """
    Platform-independent INET type.
    
    Uses PostgreSQL's INET type when available, otherwise uses String for SQLite.
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(INET())
        else:
            return dialect.type_descriptor(String(45))  # Max IPv6 length

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        return value


class AccessLevel(str, enum.Enum):
    """Access level for OAuth scopes"""
    read = "read"
    write = "write"
    admin = "admin"


class TokenEndpointAuthMethod(str, enum.Enum):
    """Token endpoint authentication method"""
    none = "none"                      # Public client (PKCE-only)
    client_secret_post = "client_secret_post"  # Secret in body
    client_secret_basic = "client_secret_basic"  # Secret in Authorization header


class ConsentMethod(str, enum.Enum):
    """Method by which user consent was obtained"""
    explicit = "explicit"    # User explicitly approved consent screen
    implicit = "implicit"    # Implied consent (e.g., continued use)
    first_party = "first_party"  # First-party app, consent implied


class OAuthScope(Base):
    """
    OAuth Scope Definition Model
    
    Defines available permission scopes for the OAuth server.
    Each scope specifies:
    - What profile fields can be accessed
    - Required context type (if any)
    - Access level (read/write/admin)
    - Whether explicit consent display is required
    """
    __tablename__ = "oauth_scopes"

    scope_name = Column(String(100), primary_key=True)
    description = Column(Text, nullable=False)
    
    # Context restriction - NULL means scope works for any context
    required_context_type = Column(
        SQLEnum(ContextType, name="context_type"),
        nullable=True
    )
    
    access_level = Column(
        SQLEnum(AccessLevel, name="oauth_access_level", create_type=False),
        nullable=False,
        default=AccessLevel.read
    )
    
    # Fields accessible with this scope (stored as TEXT[] in PostgreSQL)
    allowed_fields = Column(TextArray, nullable=True)
    
    # Sensitive scopes require explicit display in consent screen
    is_sensitive = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<OAuthScope(name={self.scope_name}, level={self.access_level})>"
    
    def allows_field(self, field_name: str) -> bool:
        """Check if this scope grants access to a specific field"""
        if self.allowed_fields is None:
            return True  # Scope grants access to all fields
        return field_name in self.allowed_fields


class OAuthClient(Base, TimestampMixin, SoftDeleteMixin):
    """
    OAuth Client Registration Model
    
    Represents a registered third-party application that can request
    authorization to access user profiles.
    
    Client Types (OAuth 2.1):
    - Confidential: Has client_secret, server-side apps
    - Public: No client_secret, mobile/SPA apps (PKCE-only)
    
    First-Party Clients:
    - Owned by the identity system operator
    - Can skip consent screen
    - Have elevated trust level
    """
    __tablename__ = "oauth_clients"

    client_id = Column(String(64), primary_key=True)
    
    # NULL for public clients (PKCE-only)
    client_secret_hash = Column(String(256), nullable=True)
    
    client_name = Column(String(255), nullable=False)
    client_description = Column(Text, nullable=True)
    client_uri = Column(Text, nullable=True)  # Homepage URL
    logo_uri = Column(Text, nullable=True)    # Logo for consent screen
    
    # Allowed callback URLs (OAuth 2.1 requires exact match)
    redirect_uris = Column(TextArray, nullable=False)
    
    # Scopes this client is allowed to request
    allowed_scopes = Column(TextArray, nullable=False, default=lambda: ['profile:read:basic'])
    
    # Default context type when client doesn't specify
    default_context_type = Column(
        SQLEnum(ContextType, name="context_type"),
        nullable=True
    )
    
    # Client classification
    is_confidential = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_first_party = Column(Boolean, nullable=False, default=False)
    
    token_endpoint_auth_method = Column(
        SQLEnum(TokenEndpointAuthMethod, name="token_endpoint_auth_method", create_type=False),
        nullable=False,
        default=TokenEndpointAuthMethod.none
    )

    # Relationships
    authorization_codes = relationship(
        "OAuthAuthorizationCode",
        back_populates="client",
        cascade="all, delete-orphan"
    )
    access_tokens = relationship(
        "OAuthAccessToken",
        back_populates="client",
        cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "OAuthRefreshToken",
        back_populates="client",
        cascade="all, delete-orphan"
    )
    consents = relationship(
        "OAuthConsent",
        back_populates="client",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        client_type = "confidential" if self.is_confidential else "public"
        return f"<OAuthClient(id={self.client_id}, name={self.client_name}, type={client_type})>"
    
    def is_redirect_uri_valid(self, redirect_uri: str) -> bool:
        """
        Validate redirect URI against registered URIs.
        OAuth 2.1 requires exact string matching (no wildcards).
        """
        return redirect_uri in (self.redirect_uris or [])
    
    def can_request_scope(self, scope: str) -> bool:
        """Check if client is allowed to request a specific scope"""
        return scope in (self.allowed_scopes or [])
    
    def can_request_scopes(self, scopes: List[str]) -> bool:
        """Check if client is allowed to request all specified scopes"""
        return all(self.can_request_scope(scope) for scope in scopes)


class OAuthAuthorizationCode(Base):
    """
    OAuth Authorization Code Model
    
    Temporary authorization code issued after user consent.
    Used in Authorization Code Flow with PKCE.
    
    Security Features:
    - 10 minute expiry (OAuth 2.1 recommendation)
    - Single-use (marked used_at on exchange)
    - PKCE mandatory (code_challenge required)
    - Bound to specific redirect_uri
    """
    __tablename__ = "oauth_authorization_codes"

    code = Column(String(128), primary_key=True)
    
    client_id = Column(
        String(64),
        ForeignKey("oauth_clients.client_id", ondelete="CASCADE"),
        nullable=False
    )
    
    user_id = Column(
        UUID(),
        ForeignKey("base_profiles.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    redirect_uri = Column(Text, nullable=False)
    scope = Column(Text, nullable=False)  # Space-separated scope string
    state = Column(String(256), nullable=True)  # Client state parameter
    
    # PKCE - mandatory in OAuth 2.1
    code_challenge = Column(String(128), nullable=False)
    code_challenge_method = Column(String(10), nullable=False, default="S256")
    
    # Optional context binding
    context_profile_id = Column(
        UUID(),
        ForeignKey("context_profiles.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # OIDC nonce for ID token
    nonce = Column(String(256), nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)  # Set when code is exchanged

    # Relationships
    client = relationship("OAuthClient", back_populates="authorization_codes")
    user = relationship("BaseProfile")
    context_profile = relationship("ContextProfile")

    def __repr__(self) -> str:
        return f"<OAuthAuthorizationCode(code={self.code[:8]}..., client={self.client_id})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if authorization code has expired"""
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return now > expires_at
    
    @property
    def is_used(self) -> bool:
        """Check if authorization code was already exchanged"""
        return self.used_at is not None
    
    @property
    def is_valid(self) -> bool:
        """Check if authorization code is valid for exchange"""
        return not self.is_expired and not self.is_used
    
    def get_scopes_list(self) -> List[str]:
        """Parse space-separated scope string into list"""
        return self.scope.split() if self.scope else []


class OAuthAccessToken(Base):
    """
    OAuth Access Token Model
    
    Short-lived access token for API authorization.
    Stored as hash for security (original token returned only once).
    
    Security Features:
    - 1 hour default expiry
    - Token stored as SHA-256 hash
    - Can be revoked by user or admin
    - Bound to specific scope and optional context
    """
    __tablename__ = "oauth_access_tokens"

    id = Column(
        UUID(),
        primary_key=True,
        default=uuid_pkg.uuid4
    )
    
    token_hash = Column(String(256), nullable=False, unique=True)
    
    client_id = Column(
        String(64),
        ForeignKey("oauth_clients.client_id", ondelete="CASCADE"),
        nullable=False
    )
    
    user_id = Column(
        UUID(),
        ForeignKey("base_profiles.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    scope = Column(Text, nullable=False)
    
    # Optional context binding for context-aware tokens
    context_profile_id = Column(
        UUID(),
        ForeignKey("context_profiles.id", ondelete="SET NULL"),
        nullable=True
    )
    
    issued_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("OAuthClient", back_populates="access_tokens")
    user = relationship("BaseProfile")
    context_profile = relationship("ContextProfile")
    refresh_token = relationship(
        "OAuthRefreshToken",
        back_populates="access_token",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<OAuthAccessToken(id={self.id}, client={self.client_id}, user={self.user_id})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if access token has expired"""
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return now > expires_at
    
    @property
    def is_revoked(self) -> bool:
        """Check if access token has been revoked"""
        return self.revoked_at is not None
    
    @property
    def is_active(self) -> bool:
        """Check if access token is valid for use"""
        return not self.is_expired and not self.is_revoked
    
    def get_scopes_list(self) -> List[str]:
        """Parse space-separated scope string into list"""
        return self.scope.split() if self.scope else []
    
    def has_scope(self, required_scope: str) -> bool:
        """Check if token has a specific scope"""
        return required_scope in self.get_scopes_list()


class OAuthRefreshToken(Base):
    """
    OAuth Refresh Token Model
    
    Long-lived token for obtaining new access tokens.
    Implements refresh token rotation as required by OAuth 2.1.
    
    Security Features:
    - 30 day default expiry
    - Token stored as SHA-256 hash
    - Rotation: new refresh token issued on each use
    - Old token tracked via replaced_by_id for audit
    - Reuse detection possible via chain tracking
    """
    __tablename__ = "oauth_refresh_tokens"

    id = Column(
        UUID(),
        primary_key=True,
        default=uuid_pkg.uuid4
    )
    
    token_hash = Column(String(256), nullable=False, unique=True)
    
    access_token_id = Column(
        UUID(),
        ForeignKey("oauth_access_tokens.id", ondelete="CASCADE"),
        nullable=False
    )
    
    client_id = Column(
        String(64),
        ForeignKey("oauth_clients.client_id", ondelete="CASCADE"),
        nullable=False
    )
    
    user_id = Column(
        UUID(),
        ForeignKey("base_profiles.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    scope = Column(Text, nullable=False)
    
    issued_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    # Rotation tracking
    rotated_at = Column(DateTime, nullable=True)  # Set when token is rotated
    replaced_by_id = Column(
        UUID(),
        ForeignKey("oauth_refresh_tokens.id"),
        nullable=True
    )  # Points to replacement token

    # Relationships
    client = relationship("OAuthClient", back_populates="refresh_tokens")
    user = relationship("BaseProfile")
    access_token = relationship("OAuthAccessToken", back_populates="refresh_token")
    replacement = relationship(
        "OAuthRefreshToken",
        remote_side=[id],
        backref="replaced_token"
    )

    def __repr__(self) -> str:
        return f"<OAuthRefreshToken(id={self.id}, client={self.client_id}, user={self.user_id})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if refresh token has expired"""
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return now > expires_at
    
    @property
    def is_revoked(self) -> bool:
        """Check if refresh token has been revoked"""
        return self.revoked_at is not None
    
    @property
    def is_rotated(self) -> bool:
        """Check if refresh token has been rotated (used and replaced)"""
        return self.rotated_at is not None
    
    @property
    def is_active(self) -> bool:
        """Check if refresh token is valid for use"""
        return not self.is_expired and not self.is_revoked and not self.is_rotated
    
    def get_scopes_list(self) -> List[str]:
        """Parse space-separated scope string into list"""
        return self.scope.split() if self.scope else []


class OAuthConsent(Base):
    """
    OAuth Consent Record Model
    
    Tracks user consent for third-party access to profile data.
    Supports GDPR-inspired consent management:
    - Explicit consent tracking
    - Consent withdrawal (Art. 7(3))
    - Consent expiry
    - Audit trail (IP, user agent)
    """
    __tablename__ = "oauth_consents"

    id = Column(
        UUID(),
        primary_key=True,
        default=uuid_pkg.uuid4
    )
    
    user_id = Column(
        UUID(),
        ForeignKey("base_profiles.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    client_id = Column(
        String(64),
        ForeignKey("oauth_clients.client_id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Scopes the user has granted
    granted_scopes = Column(TextArray, nullable=False)
    
    # Optional binding to specific context
    context_profile_id = Column(
        UUID(),
        ForeignKey("context_profiles.id", ondelete="SET NULL"),
        nullable=True
    )
    
    granted_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)  # NULL means no expiry
    withdrawn_at = Column(DateTime, nullable=True)  # Consent withdrawal
    
    consent_method = Column(
        SQLEnum(ConsentMethod, name="consent_method", create_type=False),
        nullable=False,
        default=ConsentMethod.explicit
    )
    
    # Audit trail
    ip_address = Column(InetType, nullable=True)
    user_agent = Column(Text, nullable=True)

    # Relationships
    user = relationship("BaseProfile")
    client = relationship("OAuthClient", back_populates="consents")
    context_profile = relationship("ContextProfile")

    def __repr__(self) -> str:
        status = "withdrawn" if self.withdrawn_at else "active"
        return f"<OAuthConsent(user={self.user_id}, client={self.client_id}, status={status})>"
    
    @property
    def is_withdrawn(self) -> bool:
        """Check if consent has been withdrawn"""
        return self.withdrawn_at is not None
    
    @property
    def is_expired(self) -> bool:
        """Check if consent has expired"""
        if self.expires_at is None:
            return False
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return now > expires_at
    
    @property
    def is_active(self) -> bool:
        """Check if consent is currently valid"""
        return not self.is_withdrawn and not self.is_expired
    
    def has_scope(self, scope: str) -> bool:
        """Check if consent includes a specific scope"""
        return scope in (self.granted_scopes or [])
    
    def has_all_scopes(self, scopes: List[str]) -> bool:
        """Check if consent includes all specified scopes"""
        return all(self.has_scope(scope) for scope in scopes)
