"""
Audit Log Repository

Data access layer for immutable audit logs.
Provides append-only operations with hash chain integrity.
No update or delete methods exist by design.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.models.audit import AuditLog, AuditOperation, GENESIS_HASH


class AuditRepository:
    """
    Repository for audit log operations.

    Append-only: no update or delete methods exist by design.
    """

    def __init__(self, db: Session):
        self.db = db

    def _compute_entry_hash(
        self,
        timestamp: datetime,
        event_type: str,
        user_id: Optional[str],
        actor_id: Optional[str],
        resource_type: str,
        resource_id: str,
        operation: str,
        changes: Optional[dict],
        previous_hash: str
    ) -> str:
        """
        Compute SHA-256 hash for an audit log entry.

        The hash input is a deterministic concatenation of all
        semantically significant fields plus the previous entry's hash,
        separated by pipe characters.

        Args:
            timestamp: Event timestamp (ISO format used for hashing)
            event_type: Event type string
            user_id: Data subject UUID string or None
            actor_id: Actor UUID string or None
            resource_type: Resource type string
            resource_id: Resource identifier string
            operation: Operation enum value string
            changes: JSONB changes dict (sorted keys for determinism)
            previous_hash: Hash of the previous log entry

        Returns:
            64-character hex digest of SHA-256 hash
        """
        changes_json = json.dumps(
            changes, sort_keys=True, default=str
        ) if changes else ""

        # Normalize: strip tzinfo before isoformat for consistent hashing.
        # Some databases (SQLite) strip timezone on read-back; PostgreSQL
        # preserves it. Stripping ensures identical hash inputs regardless
        # of the storage backend.
        normalized_ts = timestamp.replace(tzinfo=None)

        hash_input = "|".join([
            normalized_ts.isoformat(),
            event_type,
            str(user_id) if user_id else "",
            str(actor_id) if actor_id else "",
            resource_type,
            resource_id,
            operation,
            changes_json,
            previous_hash
        ])

        return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    def _get_latest_hash(self) -> str:
        """
        Get the entry_hash of the most recent audit log entry.

        Returns GENESIS_HASH if no entries exist yet.
        """
        latest = (
            self.db.query(AuditLog.entry_hash)
            .order_by(desc(AuditLog.created_at), desc(AuditLog.log_id))
            .first()
        )
        if latest:
            return latest[0]
        return GENESIS_HASH

    def create_log(
        self,
        event_type: str,
        user_id: Optional[UUID],
        actor_id: Optional[UUID],
        resource_type: str,
        resource_id: str,
        operation: AuditOperation,
        changes: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        legal_basis: Optional[str] = None
    ) -> AuditLog:
        """
        Create a new audit log entry with hash chaining.

        Fetches the latest entry's hash, computes this entry's hash
        incorporating it, then persists the new entry.

        Args:
            event_type: Event type string (from AuditEventType.value)
            user_id: Data subject UUID
            actor_id: Actor UUID (who performed the action)
            resource_type: Type of resource affected
            resource_id: Identifier of the resource
            operation: Operation performed
            changes: Optional dict of change details
            ip_address: Client IP address
            user_agent: Client user agent string
            legal_basis: GDPR processing basis

        Returns:
            Created AuditLog instance
        """
        now = datetime.now(timezone.utc)
        previous_hash = self._get_latest_hash()

        entry_hash = self._compute_entry_hash(
            timestamp=now,
            event_type=event_type,
            user_id=str(user_id) if user_id else None,
            actor_id=str(actor_id) if actor_id else None,
            resource_type=resource_type,
            resource_id=resource_id,
            operation=operation.value,
            changes=changes,
            previous_hash=previous_hash
        )

        log_entry = AuditLog(
            created_at=now,
            event_type=event_type,
            user_id=user_id,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            operation=operation,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            legal_basis=legal_basis,
            previous_hash=previous_hash,
            entry_hash=entry_hash
        )

        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        return log_entry

    def get_logs_for_user(
        self,
        user_id: UUID,
        event_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific user (data subject access).

        Args:
            user_id: Data subject UUID
            event_type: Optional filter by event type
            resource_type: Optional filter by resource type
            limit: Maximum entries to return
            offset: Pagination offset

        Returns:
            List of AuditLog entries, newest first
        """
        query = (
            self.db.query(AuditLog)
            .filter(AuditLog.user_id == user_id)
        )

        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)

        return (
            query.order_by(desc(AuditLog.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_logs_for_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific resource.

        Args:
            resource_type: Resource type (e.g., "profile", "context")
            resource_id: Resource identifier
            limit: Maximum entries to return
            offset: Pagination offset

        Returns:
            List of AuditLog entries, newest first
        """
        return (
            self.db.query(AuditLog)
            .filter(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id
            )
            .order_by(desc(AuditLog.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_logs_for_user(self, user_id: UUID) -> int:
        """Count total audit logs for a user."""
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .count()
        )

    def verify_chain(
        self,
        limit: int = 1000
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Verify hash chain integrity for the most recent entries.

        Walks the chain from newest to oldest, recomputing each
        entry's hash and verifying it matches the stored value.
        Also checks that each entry's previous_hash matches the
        entry_hash of the chronologically preceding entry.

        Args:
            limit: Maximum number of entries to verify

        Returns:
            Tuple of (is_valid, entries_verified, error_message)
        """
        entries = (
            self.db.query(AuditLog)
            .order_by(desc(AuditLog.created_at), desc(AuditLog.log_id))
            .limit(limit)
            .all()
        )

        if not entries:
            return True, 0, None

        entries_verified = 0
        for i, entry in enumerate(entries):
            # Recompute this entry's hash from its fields
            recomputed = self._compute_entry_hash(
                timestamp=entry.created_at,
                event_type=entry.event_type,
                user_id=str(entry.user_id) if entry.user_id else None,
                actor_id=str(entry.actor_id) if entry.actor_id else None,
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                operation=entry.operation.value,
                changes=entry.changes,
                previous_hash=entry.previous_hash
            )

            if recomputed != entry.entry_hash:
                return (
                    False,
                    entries_verified,
                    f"Hash mismatch at log_id={entry.log_id}: "
                    f"stored={entry.entry_hash}, computed={recomputed}"
                )

            # Check chain linkage: this entry's previous_hash should
            # match the older entry's entry_hash
            if i + 1 < len(entries):
                older_entry = entries[i + 1]
                if entry.previous_hash != older_entry.entry_hash:
                    return (
                        False,
                        entries_verified,
                        f"Chain break at log_id={entry.log_id}: "
                        f"previous_hash={entry.previous_hash} does not "
                        f"match older entry_hash={older_entry.entry_hash}"
                    )

            entries_verified += 1

        return True, entries_verified, None
