from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import delete

from database import AsyncSessionLocal
from models.session import Session


async def _cleanup_expired_sessions() -> str:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Session).where(Session.expires_at < datetime.now(timezone.utc)))
        await session.commit()
    return "ok"


@shared_task(name="tasks.cleanup.cleanup_old_mail")
def cleanup_old_mail() -> str:
    return asyncio.run(_cleanup_expired_sessions())
