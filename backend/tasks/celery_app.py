from celery import Celery
from celery.schedules import crontab

from config import settings

celery_app = Celery(
    "email_system",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks.delivery", "tasks.cleanup", "tasks.backup_tasks", "tasks.scheduled_email_tasks"],
)
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "cleanup-mail": {
        "task": "tasks.cleanup.cleanup_old_mail",
        "schedule": 3600.0,
    },
    "scheduled-backup": {
        "task": "tasks.backup_tasks.run_scheduled_backup",
        "schedule": crontab(hour=2, minute=0),
    },
    "process-scheduled-emails": {
        "task": "tasks.scheduled_email_tasks.process_scheduled_emails",
        "schedule": 60.0,
    },
}
