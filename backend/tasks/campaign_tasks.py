from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import text

from database import AsyncSessionLocal
from services.campaign_service import send_campaign
from tasks.celery_app import celery_app


@celery_app.task(name="tasks.campaign_tasks.send_campaign_task")
def send_campaign_task(campaign_id: str) -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            await send_campaign(campaign_id, db)

    asyncio.run(_run())


@celery_app.task(name="tasks.campaign_tasks.process_scheduled_campaigns")
def process_scheduled_campaigns() -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text(
                    """
                    SELECT id
                    FROM campaign_emails
                    WHERE status = 'scheduled'
                      AND scheduled_at <= now()
                    """
                )
            )
            rows = result.mappings().all()
            for row in rows:
                send_campaign_task.delay(str(row["id"]))

    asyncio.run(_run())
