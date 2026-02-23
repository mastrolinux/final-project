"""
Audit Log Models

SQLAlchemy model for immutable audit logging with hash chaining.
Implements tamper-evident audit trail for privacy accountability.
"""

import enum
import uuid as uuid_pkg
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text

from src.core.database import Base
from src.models.profile import UUID, JSONBType
from src.models.oauth import InetType


class AuditOperation(str, enum.Enum):
    """Audit operation types matching the database enum."""
    create = "create"
    update = "update"
    delete = "delete"
    login = "login"
    logout = "logout"
    register = "register"
    verify = "verify"
    grant = "grant"
    withdraw = "withdraw"
    revoke = "revoke"
    restore = "restore"
    review = "review"
    read = "read"


class AuditEventType(str, enum.Enum):
    """
    Audit event types.

    Stored as VARCHAR in the database to avoid migration churn.
    Enforcement is at the application layer via this enum.
    """
    # Auth events
    login_success = "auth.login.success"
    login_failure = "auth.login.failure"
    logout = "auth.logout"
    register = "auth.register"
    email_verification = "auth.email_verification"
    password_change = "auth.password_change"
    password_reset_request = "auth.password_reset_request"
    password_reset = "auth.password_reset"
    account_lock = "auth.account_lock"

    # Profile events
    profile_create = "profile.create"
    profile_update = "profile.update"
    profile_delete = "profile.delete"

    # Context events
    context_create = "context.create"
    context_update = "context.update"
    context_delete = "context.delete"

    # Consent events
    consent_grant = "consent.grant"
    consent_withdraw = "consent.withdraw"

    # Privacy events
    data_export = "privacy.data_export"
    account_deletion_requested = "privacy.account_deletion_requested"
    account_restored = "privacy.account_restored"
    account_permanently_purged = "privacy.account_permanently_purged"

    # OAuth events
    token_revoke = "oauth.token.revoke"
    client_create = "oauth.client.create"
    client_update = "oauth.client.update"
    client_delete = "oauth.client.delete"
    client_purge = "oauth.client.purge"

    # Avatar events
    avatar_upload = "avatar.upload"
    avatar_delete = "avatar.delete"

    # Verification events
    document_upload = "verification.document.upload"
    document_review = "verification.document.review"
    document_delete = "verification.document.delete"
    document_view = "verification.document.view"


# SHA-256 of b"GENESIS" - used as previous_hash for the first entry in the chain
GENESIS_HASH = "901131d838b17aac0f7885b81e03cbdc9f5157a00343d30ab22083685ed1416a"


class AuditLog(Base):
    """
    Immutable audit log entry with hash chaining.

    Each entry stores the SHA-256 hash of the previous entry, creating
    a verifiable chain. Tampering with historical entries breaks
    the chain and is detectable via verify_chain().

    Intentionally omits TimestampMixin (no updated_at) and
    SoftDeleteMixin (no deleted_at) because audit logs are immutable.
    """
    __tablename__ = "audit_logs"

    log_id = Column(
        UUID(),
        primary_key=True,
        default=lambda: str(uuid_pkg.uuid4())
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    event_type = Column(String(100), nullable=False)

    user_id = Column(
        UUID(),
        ForeignKey("base_profiles.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    actor_id = Column(
        UUID(),
        ForeignKey("base_profiles.user_id", ondelete="SET NULL"),
        nullable=True
    )

    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=False)

    operation = Column(
        SQLEnum(AuditOperation, name="audit_operation", create_type=False),
        nullable=False
    )

    changes = Column(JSONBType, nullable=True)
    ip_address = Column(InetType, nullable=True)
    user_agent = Column(Text, nullable=True)
    legal_basis = Column(String(100), nullable=True)

    previous_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), nullable=False)

    def __repr__(self):
        return (
            f"<AuditLog(log_id={self.log_id}, event={self.event_type}, "
            f"user={self.user_id}, op={self.operation})>"
        )
