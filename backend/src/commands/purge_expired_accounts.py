"""Management command to permanently delete soft-deleted accounts past their grace period.

Usage: docker compose exec api python -m src.commands.purge_expired_accounts
"""

import logging
import sys

from src.core.config import settings
from src.core.database import SessionLocal
from src.repositories.auth_repository import AuthRepository
from src.repositories.context_repository import ContextRepository
from src.repositories.oauth_repository import OAuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.repositories.audit_repository import AuditRepository
from src.services.audit_service import AuditService
from src.services.privacy_service import PrivacyService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Purge expired soft-deleted accounts."""
    retention_days = settings.DELETION_RETENTION_DAYS
    logger.info(
        "Starting purge of expired accounts (retention: %d days)",
        retention_days,
    )

    db = SessionLocal()
    try:
        profile_repo = ProfileRepository(db)
        context_repo = ContextRepository(db)
        auth_repo = AuthRepository(db)
        oauth_repo = OAuthRepository(db)
        audit_repo = AuditRepository(db)
        audit_service = AuditService(audit_repo)

        privacy_service = PrivacyService(
            profile_repo=profile_repo,
            context_repo=context_repo,
            auth_repo=auth_repo,
            oauth_repo=oauth_repo,
            audit_service=audit_service,
        )

        purged_count = privacy_service.purge_expired_accounts(retention_days)
        logger.info("Purge complete: %d accounts permanently deleted", purged_count)

    except Exception:
        logger.exception("Purge failed")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
