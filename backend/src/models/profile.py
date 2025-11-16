"""
Profile Models

SQLAlchemy models for base profiles and identity names.
Implements core identity aggregate from data architecture.
"""

from datetime import datetime, timezone
from typing import Optional
import uuid as uuid_pkg
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, 
    Enum as SQLEnum, Text, text, TypeDecorator
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.types import CHAR, JSON
from sqlalchemy.orm import relationship
import enum

from src.core.database import Base


class UUID(TypeDecorator):
    """
    Platform-independent UUID type.
    
    Uses PostgreSQL's UUID type when available, otherwise uses CHAR(36) for SQLite.
    This allows tests to run with SQLite while production uses PostgreSQL.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value) if isinstance(value, uuid_pkg.UUID) else value
        else:
            if isinstance(value, uuid_pkg.UUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid_pkg.UUID):
            return value
        return uuid_pkg.UUID(value)


class JSONBType(TypeDecorator):
    """
    Platform-independent JSONB type.
    
    Uses PostgreSQL's JSONB type when available, otherwise uses JSON for SQLite.
    This allows tests to run with SQLite while production uses PostgreSQL.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())


class AccountType(str, enum.Enum):
    """Account type enumeration"""
    verified = "verified"
    unverified = "unverified"
    pseudonymous = "pseudonymous"


class NameType(str, enum.Enum):
    """Name type enumeration"""
    given = "given"
    family = "family"
    preferred = "preferred"
    legal = "legal"
    patronymic = "patronymic"
    full_name = "full_name"
    custom = "custom"


class VisibilityLevel(str, enum.Enum):
    """Visibility level enumeration"""
    public = "public"
    private = "private"
    historical_suppressed = "historical_suppressed"


class TimestampMixin:
    """Mixin for timestamp fields"""
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    deleted_at = Column(DateTime, nullable=True)

    @property
    def is_deleted(self) -> bool:
        """Check if entity is soft-deleted"""
        return self.deleted_at is not None


class TemporalMixin:
    """Mixin for temporal validity"""
    valid_from = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    valid_to = Column(DateTime, nullable=True)

    @property
    def is_valid(self) -> bool:
        """Check if entity is currently valid"""
        now = datetime.now(timezone.utc)
        # Make stored datetimes timezone-aware for comparison if they're naive
        valid_from = self.valid_from.replace(tzinfo=timezone.utc) if self.valid_from.tzinfo is None else self.valid_from
        
        if self.valid_to is None:
            return valid_from <= now
        
        valid_to = self.valid_to.replace(tzinfo=timezone.utc) if self.valid_to.tzinfo is None else self.valid_to
        return valid_from <= now <= valid_to


class BaseProfile(Base, TimestampMixin, SoftDeleteMixin, TemporalMixin):
    """
    Base Profile Model
    
    Core user profile information. Supports three account types:
    - verified: Full access, legal name required
    - unverified: Limited access, legal name optional
    - pseudonymous: Minimal access, no legal name required
    
    Follows privacy-by-design principles with optional legal_name field.
    """
    __tablename__ = "base_profiles"

    user_id = Column(
        UUID(),
        primary_key=True,
        default=uuid_pkg.uuid4
    )
    
    account_type = Column(
        SQLEnum(AccountType, name="account_type"),
        nullable=False,
        default=AccountType.unverified
    )
    
    # Optional - only required for verified accounts accessing legal/healthcare contexts
    legal_name = Column(Text, nullable=True)
    
    primary_email = Column(String(255), nullable=False, unique=True)
    primary_phone = Column(String(50), nullable=True)
    preferred_language = Column(String(10), nullable=False, default="en")
    
    # Relationships
    identity_names = relationship(
        "IdentityName",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<BaseProfile(user_id={self.user_id}, email={self.primary_email}, type={self.account_type})>"


class IdentityName(Base, TimestampMixin, TemporalMixin):
    """
    Identity Name Model
    
    Multilingual name storage supporting diverse cultural naming conventions.
    Uses JSONB for flexible name representation across languages and scripts.
    
    Example name_value JSONB:
    - Mononym: {"en": "Sukarno"}
    - Western: {"en": "John Smith"}
    - Chinese: {"zh": "李明", "zh-Latn": "Li Ming", "en": "Li Ming"}
    - Arabic: {"ar": "محمد", "ar-Latn": "Muhammad", "en": "Muhammad"}
    
    Supports deprecated names (deadnames) with visibility controls.
    """
    __tablename__ = "identity_names"

    id = Column(
        UUID(),
        primary_key=True,
        default=uuid_pkg.uuid4
    )
    
    identity_id = Column(
        UUID(),
        ForeignKey("base_profiles.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    name_type = Column(
        SQLEnum(NameType, name="name_type"),
        nullable=False
    )
    
    # JSONB field for multilingual name storage
    # Example: {"en": "John", "es": "Juan", "zh": "约翰"}
    name_value = Column(JSONBType, nullable=False)
    
    is_primary = Column(Boolean, nullable=False, default=False)
    
    # For deadnames and historical names that should not be displayed
    is_deprecated = Column(Boolean, nullable=False, default=False)
    
    visibility_level = Column(
        SQLEnum(VisibilityLevel, name="visibility_level"),
        nullable=False,
        default=VisibilityLevel.public
    )
    
    # Future: Link to context profiles
    context_id = Column(UUID(), nullable=True)
    
    # Relationships
    profile = relationship("BaseProfile", back_populates="identity_names")

    def __repr__(self) -> str:
        return f"<IdentityName(id={self.id}, type={self.name_type}, primary={self.is_primary})>"
    
    def get_name_for_language(self, lang: str, fallback: str = "en") -> Optional[str]:
        """
        Get name value for a specific language with fallback.
        
        Args:
            lang: Language code (e.g., 'en', 'zh', 'es')
            fallback: Fallback language if requested language not found
            
        Returns:
            Name string in requested language, fallback language, or None
        """
        if not isinstance(self.name_value, dict):
            return None
        
        # Try requested language
        if lang in self.name_value:
            return self.name_value[lang]
        
        # Try fallback
        if fallback in self.name_value:
            return self.name_value[fallback]
        
        # Return first available value
        if self.name_value:
            return next(iter(self.name_value.values()))
        
        return None

