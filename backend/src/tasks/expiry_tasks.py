"""Celery periodic task that checks for expired verification documents.

Runs daily at 02:00 UTC via Celery Beat. Business logic is in
VerificationService.process_expired_documents().
"""

import logging

from src.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="check_expired_documents", bind=True, max_retries=3)
def check_expired_documents(self):
    """Find expired documents, deactivate linked contexts, and send notifications.

    Creates its own DB session (Celery workers run outside FastAPI lifecycle).
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
