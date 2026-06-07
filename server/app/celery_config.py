import os
from celery import Celery
from celery.schedules import crontab

# Initialize Celery app
celery_app = Celery(
    "AutomationDB",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

# Celery configuration
celery_app.conf.update(
    # Task routing & execution
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task timeout (30 min for scraping tasks)
    task_time_limit=30 * 60,
    task_soft_time_limit=28 * 60,
    
    # Retry configuration
    task_autoretry_for=(Exception,),
    task_max_retries=3,
    task_default_retry_delay=60,  # 1 min between retries
    
    # Result backend settings
    result_expires=3600,  # Results live 1 hour
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        # Scrape jobs every 30 minutes (continuous scraping while running)
        "scrape-jobs-continuously": {
            "task": "app.tasks.scrape_all_skills_task",
            "schedule": 30 * 60,  # 30 minutes in seconds
            "options": {"queue": "default"},
        },
        # Cleanup expired jobs daily at 2 AM UTC
        "cleanup-expired-jobs-daily": {
            "task": "app.tasks.cleanup_expired_jobs_task",
            "schedule": crontab(hour=2, minute=0),  # 2 AM UTC daily
            "options": {"queue": "default"},
        },
    },
)

# Task auto-discovery (searches for tasks in app modules)
celery_app.autodiscover_tasks(["app"])


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f"Request: {self.request!r}")
