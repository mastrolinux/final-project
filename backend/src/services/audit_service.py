"""
Audit Logging Service

Business logic for immutable audit logging and trail queries.
"""

import logging
from uuid import UUID

from src.models.audit import AuditEventType, AuditOperation
from src.repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


class AuditService:
    """Service for audit logging operations."""

    def __init__(self, audit_repo: AuditRepository):
        self.audit_repo = audit_repo

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: UUID | None,
        actor_id: UUID | None,
        resource_type: str,
        resource_id: str,
        operation: AuditOperation,
        changes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        legal_basis: str | None = None,
    ) -> None:
        """Record an audit event. Swallows exceptions to avoid disrupting the caller."""
        try:
            self.audit_repo.create_log(
                event_type=event_type.value,
                user_id=user_id,
                actor_id=actor_id,
                resource_type=resource_type,
                resource_id=resource_id,
                operation=operation,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
                legal_basis=legal_basis,
            )
        except Exception:
            logger.exception(
                "Failed to record audit event: %s for user %s", event_type.value, user_id
            )

    def get_user_audit_trail(
        self,
        user_id: UUID,
        event_type: str | None = None,
        resource_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Return paginated audit trail for a user (GDPR Art. 15 access right)."""
        entries = self.audit_repo.get_logs_for_user(
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            limit=limit,
            offset=offset,
        )
        total = self.audit_repo.count_logs_for_user(user_id)

        return {"entries": entries, "total": total, "limit": limit, "offset": offset}

    def verify_integrity(self, limit: int = 1000) -> tuple[bool, int, str | None]:
        """Verify audit log hash chain integrity for tamper detection."""
        return self.audit_repo.verify_chain(limit=limit)
