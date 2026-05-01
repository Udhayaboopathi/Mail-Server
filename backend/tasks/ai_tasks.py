from __future__ import annotations

import json

import redis.asyncio as redis
from sqlalchemy import text

from config import settings
from imap.maildir import MaildirBackend
from services.ai_service import rank_emails_by_priority, suggest_labels
from tasks.celery_app import celery_app
from database import AsyncSessionLocal

_backend = MaildirBackend()


@celery_app.task(name="tasks.ai_tasks.process_priority_inbox")
def process_priority_inbox(mailbox_id: str) -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            items = _backend.list_messages(str(mailbox_id), "Inbox")[:100]
            emails = [
                {
                    "uid": item.get("uid"),
                    "from": item.get("from"),
                    "subject": item.get("subject"),
                    "preview": "",
                    "date": item.get("date"),
                }
                for item in items
            ]
            ranked = await rank_emails_by_priority(emails, {"frequent_senders": [], "keywords": []})
            client = redis.from_url(settings.redis_url, decode_responses=True)
            await client.set(f"priority_inbox:{mailbox_id}", json.dumps(ranked), ex=900)

    import asyncio

    asyncio.run(_run())


@celery_app.task(name="tasks.ai_tasks.process_priority_inbox_all")
def process_priority_inbox_all() -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("SELECT id FROM mailboxes WHERE is_active = true")
            )
            for row in result.mappings().all():
                process_priority_inbox.delay(str(row["id"]))

    import asyncio

    asyncio.run(_run())


@celery_app.task(name="tasks.ai_tasks.auto_label_incoming")
def auto_label_incoming(mailbox_id: str, email_uid: int) -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            message = _backend.read_message(str(mailbox_id), "Inbox", email_uid)
            if message is None:
                return
            result = await db.execute(
                text("SELECT name FROM labels WHERE mailbox_id = :mailbox_id"),
                {"mailbox_id": str(mailbox_id)},
            )
            existing = [row["name"] for row in result.mappings().all()]
            suggestions = await suggest_labels(
                {"from": message.get("From", ""), "subject": message.get("Subject", ""), "body": message.get_payload()},
                existing,
            )
            for name in suggestions:
                label_id_row = await db.execute(
                    text("SELECT id FROM labels WHERE mailbox_id = :mailbox_id AND name = :name"),
                    {"mailbox_id": str(mailbox_id), "name": name},
                )
                label_row = label_id_row.mappings().first()
                if not label_row:
                    continue
                await db.execute(
                    text(
                        """
                        INSERT INTO email_labels (email_uid, label_id, mailbox_id)
                        VALUES (:email_uid, :label_id, :mailbox_id)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"email_uid": str(email_uid), "label_id": str(label_row["id"]), "mailbox_id": str(mailbox_id)},
                )
            await db.commit()

    import asyncio

    asyncio.run(_run())
