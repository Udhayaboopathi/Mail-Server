from __future__ import annotations

import redis.asyncio as redis
from sqlalchemy import text

from config import settings
from database import AsyncSessionLocal
from smtp.outbound import deliver_outbound
from tasks.celery_app import celery_app


@celery_app.task(name="tasks.storage_alert_tasks.check_storage_alerts")
def check_storage_alerts() -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            client = redis.from_url(settings.redis_url, decode_responses=True)
            domains = await db.execute(text("SELECT id, name FROM domains"))
            for domain in domains.mappings().all():
                usage = await db.execute(
                    text(
                        """
                        SELECT COALESCE(SUM(used_mb), 0) AS used_mb, COALESCE(SUM(quota_mb), 0) AS quota_mb
                        FROM mailboxes
                        WHERE domain_id = :domain_id
                        """
                    ),
                    {"domain_id": str(domain["id"])},
                )
                row = usage.mappings().first()
                used_gb = float(row["used_mb"]) / 1024
                quota_gb = max(float(row["quota_mb"]) / 1024, 1)
                ratio = used_gb / quota_gb

                admin_row = await db.execute(
                    text("SELECT email FROM users WHERE is_admin = true ORDER BY created_at ASC LIMIT 1")
                )
                admin = admin_row.mappings().first()
                if not admin:
                    continue

                if ratio >= 1.0:
                    key = f"storage_alert:{domain['id']}:critical"
                    if not await client.get(key):
                        await client.set(key, "1", ex=86400)
                        message = {
                            "from": f"no-reply@{settings.smtp_hostname}",
                            "to": admin["email"],
                            "subject": f"Storage quota exceeded for {domain['name']}",
                            "body_text": f"Domain {domain['name']} has exceeded its storage quota.",
                        }
                        from email.message import EmailMessage

                        msg = EmailMessage()
                        msg["From"] = message["from"]
                        msg["To"] = message["to"]
                        msg["Subject"] = message["subject"]
                        msg.set_content(message["body_text"])
                        await deliver_outbound(msg, admin["email"])
                        await db.execute(
                            text("UPDATE domains SET is_active = false WHERE id = :id"),
                            {"id": str(domain["id"])},
                        )
                elif ratio >= 0.8:
                    key = f"storage_alert:{domain['id']}:warn"
                    if not await client.get(key):
                        await client.set(key, "1", ex=86400)
                        from email.message import EmailMessage

                        msg = EmailMessage()
                        msg["From"] = f"no-reply@{settings.smtp_hostname}"
                        msg["To"] = admin["email"]
                        msg["Subject"] = f"Storage nearing limit for {domain['name']}"
                        msg.set_content(f"Domain {domain['name']} is at {ratio:.0%} of storage quota.")
                        await deliver_outbound(msg, admin["email"])
            await db.commit()

    import asyncio

    asyncio.run(_run())
