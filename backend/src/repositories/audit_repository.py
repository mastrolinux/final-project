"""
Audit Log Repository

Data access layer for immutable audit logs.
Provides append-only operations with hash chain integrity.
No update or delete methods exist by design.
"""

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.models.audit import GENESIS_HASH, AuditLog, AuditOperation


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
        user_id: str | None,
        actor_id: str | None,
        resource_type: str,
        resource_id: str,
        operation: str,
        changes: dict | None,
        previous_hash: str,
    ) -> str:
        """Compute SHA-256 hash for an audit log entry.

        Concatenates all significant fields plus the previous entry's
        hash with pipe separators for deterministic chaining.
        """
        changes_json = json.dumps(changes, sort_keys=True, default=str) if changes else ""

        # Normalize: strip tzinfo before isoformat for consistent hashing.
        # Some databases (SQLite) strip timezone on read-back; PostgreSQL
        # preserves it. Stripping ensures identical hash inputs regardless
        # of the storage backend.
        normalized_ts = timestamp.replace(tzinfo=None)

        hash_input = "|".join(
            [
                normalized_ts.isoformat(),
                event_type,
                str(user_id) if user_id else "",
                str(actor_id) if actor_id else "",
                resource_type,
                resource_id,
                operation,
                changes_json,
                previous_hash,
            ]
        )

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
        user_id: UUID | None,
        actor_id: UUID | None,
        resource_type: str,
        resource_id: str,
        operation: AuditOperation,
        changes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        legal_basis: str | None = None,
    ) -> AuditLog:
        """Create a new audit log entry with hash chaining."""
        now = datetime.now(UTC)
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
            previous_hash=previous_hash,
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
            entry_hash=entry_hash,
        )

        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        return log_entry

    def get_logs_for_user(
        self,
        user_id: UUID,
        event_type: str | None = None,
        resource_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Get audit logs for a specific user, newest first."""
        query = self.db.query(AuditLog).filter(AuditLog.user_id == user_id)

        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)

        return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()

    def get_logs_for_resource(
        self, resource_type: str, resource_id: str, limit: int = 50, offset: int = 0
    ) -> list[AuditLog]:
        """Get audit logs for a specific resource, newest first."""
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.resource_type == resource_type, AuditLog.resource_id == resource_id)
            .order_by(desc(AuditLog.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_logs_for_user(self, user_id: UUID) -> int:
        """Count total audit logs for a user."""
        return self.db.query(AuditLog).filter(AuditLog.user_id == user_id).count()

    def verify_chain(self, limit: int = 1000) -> tuple[bool, int, str | None]:
        """Verify hash chain integrity for the most recent entries.

        Walks newest to oldest, recomputing each hash and checking
        that previous_hash links match. Returns (is_valid,
        entries_verified, error_message).
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
            recomputed = self._compute_entry_hash(
                timestamp=entry.created_at,
                event_type=entry.event_type,
                user_id=str(entry.user_id) if entry.user_id else None,
                actor_id=str(entry.actor_id) if entry.actor_id else None,
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                operation=entry.operation.value,
                changes=entry.changes,
                previous_hash=entry.previous_hash,
            )

            if recomputed != entry.entry_hash:
                return (
                    False,
                    entries_verified,
                    f"Hash mismatch at log_id={entry.log_id}: "
                    f"stored={entry.entry_hash}, computed={recomputed}",
                )

            if i + 1 < len(entries):
                older_entry = entries[i + 1]
                if entry.previous_hash != older_entry.entry_hash:
                    return (
                        False,
                        entries_verified,
                        f"Chain break at log_id={entry.log_id}: "
                        f"previous_hash={entry.previous_hash} does not "
                        f"match older entry_hash={older_entry.entry_hash}",
                    )

            entries_verified += 1

        return True, entries_verified, None
