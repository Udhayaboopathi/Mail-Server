from celery import Celery
from celery.schedules import crontab

from config import settings

celery_app = Celery(
    "email_system",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "tasks.delivery",
        "tasks.cleanup",
        "tasks.backup_tasks",
        "tasks.scheduled_email_tasks",
        "tasks.ai_tasks",
        "tasks.campaign_tasks",
        "tasks.retention_tasks",
        "tasks.storage_alert_tasks",
    ],
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
    "process-scheduled-campaigns": {
        "task": "tasks.campaign_tasks.process_scheduled_campaigns",
        "schedule": 300.0,
    },
    "check-storage-alerts": {
        "task": "tasks.storage_alert_tasks.check_storage_alerts",
        "schedule": 3600.0,
    },
    "enforce-retention": {
        "task": "tasks.retention_tasks.enforce_retention_policies",
        "schedule": crontab(hour=3, minute=0),
    },
    "process-priority-inbox": {
        "task": "tasks.ai_tasks.process_priority_inbox_all",
        "schedule": 1800.0,
    },
}
