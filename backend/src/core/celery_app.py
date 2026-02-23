"""
Celery Application Configuration

Configures Celery for async task processing (email sending, periodic
maintenance tasks). Uses Redis as message broker and result backend.

Queues:
    emails - outbound email delivery (verification, reset, etc.)
    maintenance - periodic background jobs (document expiry checks)

Beat schedule:
    check_expired_documents - runs every 8 hours
"""

from celery import Celery
from celery.schedules import crontab

from src.core.config import settings


# Initialize Celery app
celery_app = Celery(
    "thesis_auth",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "send_verification_email": {"queue": "emails"},
        "send_password_reset_email": {"queue": "emails"},
        "send_restoration_email": {"queue": "emails"},
        "send_rejection_email": {"queue": "emails"},
        "send_approval_email": {"queue": "emails"},
        "send_document_expiry_email": {"queue": "emails"},
        "check_expired_documents": {"queue": "maintenance"},
    },
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time for email queue
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    imports=[
        "src.tasks.email_tasks",
        "src.tasks.expiry_tasks",
    ],
    beat_schedule={
        "check-expired-documents-daily": {
            "task": "check_expired_documents",
            "schedule": crontab(minute=0, hour="*/8"),  # Every 8 hours
        },
    },
)

