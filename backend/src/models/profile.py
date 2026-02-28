"""
Profile Models

SQLAlchemy models for base profiles and identity names.
Implements core identity aggregate from data architecture.
"""

import enum
import uuid as uuid_pkg
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, TypeDecorator
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import CHAR, JSON

from src.core.database import Base


class UUID(TypeDecorator):
    """Platform-independent UUID type (PostgreSQL UUID or SQLite CHAR(36))."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
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
    """Platform-independent JSONB type (PostgreSQL JSONB or SQLite JSON)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
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

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""

    deleted_at = Column(DateTime, nullable=True)

    @property
    def is_deleted(self) -> bool:
        """Check if entity is soft-deleted"""
        return self.deleted_at is not None


class TemporalMixin:
    """Mixin for temporal validity"""

    valid_from = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    valid_to = Column(DateTime, nullable=True)

    @property
    def is_valid(self) -> bool:
        """Check if entity is currently valid"""
        now = datetime.now(UTC)
        # Make stored datetimes timezone-aware for comparison if they're naive
        valid_from = (
            self.valid_from.replace(tzinfo=UTC)
            if self.valid_from.tzinfo is None
            else self.valid_from
        )

        if self.valid_to is None:
            return valid_from <= now

        valid_to = (
            self.valid_to.replace(tzinfo=UTC) if self.valid_to.tzinfo is None else self.valid_to
        )
        return valid_from <= now <= valid_to


class BaseProfile(Base, TimestampMixin, SoftDeleteMixin, TemporalMixin):
    """Core user profile with three account types (verified, unverified, pseudonymous)."""

    __tablename__ = "base_profiles"

    user_id = Column[Any](UUID(), primary_key=True, default=uuid_pkg.uuid4)

    account_type = Column[str](
        SQLEnum(AccountType, name="account_type"), nullable=False, default=AccountType.unverified
    )

    legal_name = Column[str](Text, nullable=True)

    primary_email = Column[str](String(255), nullable=False, unique=True)
    primary_phone = Column[str](String(50), nullable=True)
    preferred_language = Column[str](String(10), nullable=False, default="en")

    avatar_url = Column[str](Text, nullable=True)
    avatar_thumbnail_url = Column[str](Text, nullable=True)
    avatar_storage_path = Column[str](Text, nullable=True)

    identity_names = relationship(
        "IdentityName", back_populates="profile", cascade="all, delete-orphan", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return (
            f"<BaseProfile(user_id={self.user_id},"
            f" email={self.primary_email},"
            f" type={self.account_type})>"
        )


class IdentityName(Base, TimestampMixin, TemporalMixin):
    """Multilingual name storage using JSONB with deprecation and visibility controls."""

    __tablename__ = "identity_names"

    id = Column(UUID(), primary_key=True, default=uuid_pkg.uuid4)

    identity_id = Column(
        UUID(), ForeignKey("base_profiles.user_id", ondelete="CASCADE"), nullable=False
    )

    name_type = Column(SQLEnum(NameType, name="name_type"), nullable=False)

    name_value = Column(JSONBType, nullable=False)

    is_primary = Column(Boolean, nullable=False, default=False)

    is_deprecated = Column(Boolean, nullable=False, default=False)

    visibility_level = Column(
        SQLEnum(VisibilityLevel, name="visibility_level"),
        nullable=False,
        default=VisibilityLevel.public,
    )

    context_id = Column(UUID(), nullable=True)

    profile = relationship("BaseProfile", back_populates="identity_names")

    def __repr__(self) -> str:
        return f"<IdentityName(id={self.id}, type={self.name_type}, primary={self.is_primary})>"

    def get_name_for_language(self, lang: str, fallback: str = "en") -> str | None:
        """Get name value for a language with fallback chain.

        Fallback order: lang -> fallback -> first available.
        """
        if not isinstance(self.name_value, dict):
            return None

        if lang in self.name_value:
            return self.name_value[lang]

        if fallback in self.name_value:
            return self.name_value[fallback]

        if self.name_value:
            return next(iter(self.name_value.values()))

        return None
