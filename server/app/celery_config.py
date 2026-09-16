from celery import Celery
from celery.schedules import crontab

from app.core.config import settings


celery_app = Celery(
    "CareerSync",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)


celery_app.conf.update(

    # -----------------------------------------------------
    # Serialization
    # -----------------------------------------------------

    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # -----------------------------------------------------
    # Timezone
    # -----------------------------------------------------

    timezone="Asia/Kolkata",
    enable_utc=True,

    # -----------------------------------------------------
    # Worker settings
    # -----------------------------------------------------

    task_time_limit=30 * 60,
    task_soft_time_limit=28 * 60,

    worker_prefetch_multiplier=1,

    task_acks_late=True,

    # -----------------------------------------------------
    # Retry
    # -----------------------------------------------------

    task_autoretry_for=(Exception,),
    task_max_retries=3,
    task_default_retry_delay=60,

    # -----------------------------------------------------
    # Results
    # -----------------------------------------------------

    result_expires=3600,

    # -----------------------------------------------------
    # CELERY BEAT
    #
    # Global scraping only.
    # No user-specific scraping.
    # -----------------------------------------------------

    beat_schedule={

        # ---------------------------------------------
        # Every day at 1:00 AM IST
        # ---------------------------------------------

        "global-job-scrape-daily": {

            "task":
                "app.tasks.scrape_all_skills_task",

            "schedule":
                crontab(
                    hour=00,
                    minute=20,
                ),

            # "options": {
            #     "queue": "default"
            # },
        },


        # ---------------------------------------------
        # Every day at 2:00 AM IST
        #
        # Delete jobs whose expires_at has passed.
        # ---------------------------------------------

        "cleanup-expired-jobs-daily": {

            "task":
                "app.tasks.cleanup_expired_jobs_task",

            "schedule":
                crontab(
                    hour=2,
                    minute=0,
                ),

            # "options": {
            #     "queue": "default"
            # },
        },
    },
)


celery_app.autodiscover_tasks(
    ["app"]
)


@celery_app.task(bind=True)
def debug_task(self):

    print(
        f"Request: {self.request!r}"
    )