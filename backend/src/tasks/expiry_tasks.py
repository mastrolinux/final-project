"""
Document Expiry Tasks

Celery periodic task that checks for expired verification documents
and deactivates their linked context profiles. Runs daily via Celery
Beat at 02:00 UTC.

The business logic lives in VerificationService.process_expired_documents().
This module provides only the Celery task wrapper that manages the
database session lifecycle and retry semantics.
"""

import logging

from src.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="check_expired_documents", bind=True, max_retries=3)
def check_expired_documents(self):
    """
    Daily periodic task: find verified documents past their expiry
    date, deactivate linked contexts, and send notifications.

    Creates its own database session because Celery workers run
    outside the FastAPI request lifecycle.

    Returns:
        Dict with expired_documents and deactivated_contexts counts.
    """
    from src.core.database import SessionLocal
    from src.repositories.context_repository import ContextRepository
    from src.repositories.profile_repository import ProfileRepository
    from src.repositories.verification_repository import (
        VerificationRepository,
    )
    from src.services.audit_service import AuditService
    from src.repositories.audit_repository import AuditRepository
    from src.services.verification_service import VerificationService

    db = SessionLocal()
    try:
        service = VerificationService(
            verification_repo=VerificationRepository(db),
            profile_repo=ProfileRepository(db),
            audit_service=AuditService(AuditRepository(db)),
            context_repo=ContextRepository(db),
        )
        result = service.process_expired_documents()
        logger.info("check_expired_documents completed: %s", result)
        return result
    except Exception as exc:
        logger.error(
            "check_expired_documents failed: %s", exc, exc_info=True
        )
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    finally:
        db.close()
