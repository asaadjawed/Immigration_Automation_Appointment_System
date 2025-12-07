"""
Celery configuration for asynchronous task processing.
"""
from celery import Celery
from app.config import settings

# Create Celery instance
celery_app = Celery(
    "immigration_automation",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.email_worker"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    worker_prefetch_multiplier=1,  # Process one task at a time
    # Windows-specific: Use solo pool instead of prefork (multiprocessing issues on Windows)
    worker_pool="solo",  # Use solo pool for Windows compatibility
)

