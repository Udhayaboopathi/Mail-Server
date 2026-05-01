from __future__ import annotations

import asyncio

from tasks.celery_app import celery_app
from services.backup_service import schedule_auto_backup


@celery_app.task(name="tasks.backup_tasks.run_scheduled_backup")
def run_scheduled_backup() -> None:
    asyncio.run(schedule_auto_backup())
