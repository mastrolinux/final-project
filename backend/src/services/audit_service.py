"""
Audit Logging Service

Business logic layer for immutable audit logging.
Provides a simple interface for recording audit events
and querying audit trails.
"""

import logging
from typing import List, Optional, Tuple
from uuid import UUID

from src.models.audit import AuditOperation, AuditEventType
from src.repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


class AuditService:
    """Service for audit logging operations."""

    def __init__(self, audit_repo: AuditRepository):
        self.audit_repo = audit_repo

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[UUID],
        actor_id: Optional[UUID],
        resource_type: str,
        resource_id: str,
        operation: AuditOperation,
        changes: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        legal_basis: Optional[str] = None
    ) -> None:
        """
        Record an audit event.

        This method catches all exceptions to avoid disrupting
        the primary operation. Errors are logged but not propagated.

        Args:
            event_type: Categorized event type
            user_id: Data subject UUID
            actor_id: Actor UUID (who performed the action)
            resource_type: e.g., "profile", "context", "auth_user", "oauth_consent"
            resource_id: e.g., user_id string, context_id string
            operation: CRUD-like operation
            changes: Optional dict of change details
            ip_address: Client IP
            user_agent: Client user agent
            legal_basis: GDPR basis (e.g., "consent", "legitimate_interest", "contract")
        """
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
                legal_basis=legal_basis
            )
        except Exception:
            # Audit logging failures must not break primary operations.
            # In production, this would route to a secondary logging system.
            logger.exception(
                "Failed to record audit event: %s for user %s",
                event_type.value,
                user_id
            )

    def get_user_audit_trail(
        self,
        user_id: UUID,
        event_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """
        Get audit trail for a user (data subject access right).

        Returns paginated audit log entries for the specified user.

        Args:
            user_id: Data subject UUID
            event_type: Optional event type filter
            resource_type: Optional resource type filter
            limit: Max entries per page
            offset: Pagination offset

        Returns:
            Dict with entries list, total count, and pagination info
        """
        entries = self.audit_repo.get_logs_for_user(
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            limit=limit,
            offset=offset
        )
        total = self.audit_repo.count_logs_for_user(user_id)

        return {
            "entries": entries,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    def verify_integrity(
        self,
        limit: int = 1000
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Verify audit log hash chain integrity.

        Admin-only operation for tamper detection.

        Args:
            limit: Number of recent entries to verify

        Returns:
            Tuple of (is_valid, entries_verified, error_message)
        """
        return self.audit_repo.verify_chain(limit=limit)
