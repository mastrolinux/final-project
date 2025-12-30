"""
Celery Application Configuration

Configures Celery for async task processing, primarily for email sending.
Uses Redis as message broker and result backend.
"""

from celery import Celery
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
        "send_guardian_notification_email": {"queue": "emails"}
    },
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time for email queue
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    imports=["src.tasks.email_tasks"]  # Explicitly import task modules
)

