"""
OAuth 2.1 Models

SQLAlchemy models for OAuth 2.1 authorization server.
Implements OAuth 2.1 draft specification with mandatory PKCE,
refresh token rotation, and context-aware token binding.
"""

import enum
import json
import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, TypeDecorator
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from src.core.database import Base
from src.models.context import ContextType
from src.models.profile import UUID, SoftDeleteMixin, TimestampMixin


class TextArray(TypeDecorator):
    """Platform-independent TEXT[] type (PostgreSQL ARRAY or SQLite JSON)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_ARRAY(Text))
        else:
            return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        else:
            return json.dumps(value) if isinstance(value, list) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        else:
            if isinstance(value, str):
                return json.loads(value)
            return value


class InetType(TypeDecorator):
    """Platform-independent INET type (PostgreSQL INET or SQLite String)."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
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

    none = "none"  # Public client (PKCE-only)
    client_secret_post = "client_secret_post"  # Secret in body
    client_secret_basic = "client_secret_basic"  # Secret in Authorization header


class ConsentMethod(str, enum.Enum):
    """Method by which user consent was obtained"""

    explicit = "explicit"  # User explicitly approved consent screen
    implicit = "implicit"  # Implied consent (e.g., continued use)
    first_party = "first_party"  # First-party app, consent implied


class OAuthScope(Base):
    """OAuth scope definition with field-level access control."""

    __tablename__ = "oauth_scopes"

    scope_name = Column(String(100), primary_key=True)
    description = Column(Text, nullable=False)

    required_context_type = Column(SQLEnum(ContextType, name="context_type"), nullable=True)

    access_level = Column(
        SQLEnum(AccessLevel, name="oauth_access_level", create_type=False),
        nullable=False,
        default=AccessLevel.read,
    )

    allowed_fields = Column(TextArray, nullable=True)
    is_sensitive = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        return f"<OAuthScope(name={self.scope_name}, level={self.access_level})>"

    def allows_field(self, field_name: str) -> bool:
        """Check if this scope grants access to a specific field"""
        if self.allowed_fields is None:
            return True  # Scope grants access to all fields
        return field_name in self.allowed_fields


class OAuthClient(Base, TimestampMixin, SoftDeleteMixin):
    """Registered OAuth 2.1 client (confidential or public)."""

    __tablename__ = "oauth_clients"

    client_id = Column(String(64), primary_key=True)

    client_secret_hash = Column(String(256), nullable=True)

    client_name = Column(String(255), nullable=False)
    client_description = Column(Text, nullable=True)
    client_uri = Column(Text, nullable=True)
    logo_uri = Column(Text, nullable=True)

    redirect_uris = Column(TextArray, nullable=False)
    allowed_scopes = Column(TextArray, nullable=False, default=lambda: ["profile:read:basic"])

    default_context_type = Column(SQLEnum(ContextType, name="context_type"), nullable=True)

    is_confidential = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_first_party = Column(Boolean, nullable=False, default=False)

    token_endpoint_auth_method = Column(
        SQLEnum(TokenEndpointAuthMethod, name="token_endpoint_auth_method", create_type=False),
        nullable=False,
        default=TokenEndpointAuthMethod.none,
    )

    authorization_codes = relationship(
        "OAuthAuthorizationCode", back_populates="client", cascade="all, delete-orphan"
    )
    access_tokens = relationship(
        "OAuthAccessToken", back_populates="client", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "OAuthRefreshToken", back_populates="client", cascade="all, delete-orphan"
    )
    consents = relationship("OAuthConsent", back_populates="client", cascade="all, delete-orphan")

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

    def can_request_scopes(self, scopes: list[str]) -> bool:
        """Check if client is allowed to request all specified scopes"""
        return all(self.can_request_scope(scope) for scope in scopes)


class OAuthAuthorizationCode(Base):
    """Single-use authorization code with mandatory PKCE (10-minute expiry)."""

    __tablename__ = "oauth_authorization_codes"

    code = Column(String(128), primary_key=True)

    client_id = Column(
        String(64), ForeignKey("oauth_clients.client_id", ondelete="CASCADE"), nullable=False
    )

    user_id = Column(
        UUID(), ForeignKey("base_profiles.user_id", ondelete="CASCADE"), nullable=False
    )

    redirect_uri = Column(Text, nullable=False)
    scope = Column(Text, nullable=False)
    state = Column(String(256), nullable=True)

    code_challenge = Column(String(128), nullable=False)
    code_challenge_method = Column(String(10), nullable=False, default="S256")

    context_profile_id = Column(
        UUID(), ForeignKey("context_profiles.id", ondelete="SET NULL"), nullable=True
    )

    nonce = Column(String(256), nullable=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    client = relationship("OAuthClient", back_populates="authorization_codes")
    user = relationship("BaseProfile")
    context_profile = relationship("ContextProfile")

    def __repr__(self) -> str:
        return f"<OAuthAuthorizationCode(code={self.code[:8]}..., client={self.client_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if authorization code has expired"""
        now = datetime.now(UTC)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return now > expires_at

    @property
    def is_used(self) -> bool:
        """Check if authorization code was already exchanged"""
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if authorization code is valid for exchange"""
        return not self.is_expired and not self.is_used

    def get_scopes_list(self) -> list[str]:
        """Parse space-separated scope string into list"""
        return self.scope.split() if self.scope else []


class OAuthAccessToken(Base):
    """Short-lived access token stored as SHA-256 hash (1-hour default expiry)."""

    __tablename__ = "oauth_access_tokens"

    id = Column(UUID(), primary_key=True, default=uuid_pkg.uuid4)

    token_hash = Column(String(256), nullable=False, unique=True)

    client_id = Column(
        String(64), ForeignKey("oauth_clients.client_id", ondelete="CASCADE"), nullable=False
    )

    user_id = Column(
        UUID(), ForeignKey("base_profiles.user_id", ondelete="CASCADE"), nullable=False
    )

    scope = Column(Text, nullable=False)

    context_profile_id = Column(
        UUID(), ForeignKey("context_profiles.id", ondelete="SET NULL"), nullable=True
    )

    issued_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    client = relationship("OAuthClient", back_populates="access_tokens")
    user = relationship("BaseProfile")
    context_profile = relationship("ContextProfile")
    refresh_token = relationship(
        "OAuthRefreshToken",
        back_populates="access_token",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<OAuthAccessToken(id={self.id}, client={self.client_id}, user={self.user_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if access token has expired"""
        now = datetime.now(UTC)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return now > expires_at

    @property
    def is_revoked(self) -> bool:
        """Check if access token has been revoked"""
        return self.revoked_at is not None

    @property
    def is_active(self) -> bool:
        """Check if access token is valid for use"""
        return not self.is_expired and not self.is_revoked

    def get_scopes_list(self) -> list[str]:
        """Parse space-separated scope string into list"""
        return self.scope.split() if self.scope else []

    def has_scope(self, required_scope: str) -> bool:
        """Check if token has a specific scope"""
        return required_scope in self.get_scopes_list()


class OAuthRefreshToken(Base):
    """Long-lived refresh token with rotation (30-day default expiry)."""

    __tablename__ = "oauth_refresh_tokens"

    id = Column(UUID(), primary_key=True, default=uuid_pkg.uuid4)

    token_hash = Column(String(256), nullable=False, unique=True)

    access_token_id = Column(
        UUID(), ForeignKey("oauth_access_tokens.id", ondelete="CASCADE"), nullable=False
    )

    client_id = Column(
        String(64), ForeignKey("oauth_clients.client_id", ondelete="CASCADE"), nullable=False
    )

    user_id = Column(
        UUID(), ForeignKey("base_profiles.user_id", ondelete="CASCADE"), nullable=False
    )

    scope = Column(Text, nullable=False)

    issued_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    rotated_at = Column(DateTime, nullable=True)
    replaced_by_id = Column(UUID(), ForeignKey("oauth_refresh_tokens.id"), nullable=True)

    client = relationship("OAuthClient", back_populates="refresh_tokens")
    user = relationship("BaseProfile")
    access_token = relationship("OAuthAccessToken", back_populates="refresh_token")
    replacement = relationship("OAuthRefreshToken", remote_side=[id], backref="replaced_token")

    def __repr__(self) -> str:
        return f"<OAuthRefreshToken(id={self.id}, client={self.client_id}, user={self.user_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if refresh token has expired"""
        now = datetime.now(UTC)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
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

    def get_scopes_list(self) -> list[str]:
        """Parse space-separated scope string into list"""
        return self.scope.split() if self.scope else []


class OAuthConsent(Base):
    """User consent record with GDPR-inspired withdrawal and expiry support."""

    __tablename__ = "oauth_consents"

    id = Column(UUID(), primary_key=True, default=uuid_pkg.uuid4)

    user_id = Column(
        UUID(), ForeignKey("base_profiles.user_id", ondelete="CASCADE"), nullable=False
    )

    client_id = Column(
        String(64), ForeignKey("oauth_clients.client_id", ondelete="CASCADE"), nullable=False
    )

    granted_scopes = Column(TextArray, nullable=False)

    context_profile_id = Column(
        UUID(), ForeignKey("context_profiles.id", ondelete="SET NULL"), nullable=True
    )

    granted_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime, nullable=True)
    withdrawn_at = Column(DateTime, nullable=True)

    consent_method = Column(
        SQLEnum(ConsentMethod, name="consent_method", create_type=False),
        nullable=False,
        default=ConsentMethod.explicit,
    )

    ip_address = Column(InetType, nullable=True)
    user_agent = Column(Text, nullable=True)

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
        now = datetime.now(UTC)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return now > expires_at

    @property
    def is_active(self) -> bool:
        """Check if consent is currently valid"""
        return not self.is_withdrawn and not self.is_expired

    def has_scope(self, scope: str) -> bool:
        """Check if consent includes a specific scope"""
        return scope in (self.granted_scopes or [])

    def has_all_scopes(self, scopes: list[str]) -> bool:
        """Check if consent includes all specified scopes"""
        return all(self.has_scope(scope) for scope in scopes)
