"""
Celery Application Configuration
================================

Background task processing for document ingestion and indexing.
"""

from celery import Celery
from app.core.config import settings

# Create Celery application
celery_app = Celery(
    "knowledge_base",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.services.tasks.document_tasks",
        "app.services.tasks.indexing_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    
    # Result settings
    result_expires=86400,  # 24 hours
    
    # Rate limiting
    task_default_rate_limit="100/m",
    
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-expired-uploads": {
            "task": "app.services.tasks.document_tasks.cleanup_expired_uploads",
            "schedule": 3600.0,  # Every hour
        },
        "update-index-stats": {
            "task": "app.services.tasks.indexing_tasks.update_index_stats",
            "schedule": 300.0,  # Every 5 minutes
        },
    },
)

# Task routing
celery_app.conf.task_routes = {
    "app.services.tasks.document_tasks.*": {"queue": "documents"},
    "app.services.tasks.indexing_tasks.*": {"queue": "indexing"},
}