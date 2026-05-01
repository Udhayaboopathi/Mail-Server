from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import text

from database import AsyncSessionLocal
from tasks.celery_app import celery_app
from services.mail_service import MailService


async def _process() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT id, mailbox_id, to_addresses, cc_addresses, bcc_addresses,
                       subject, body_text, body_html, attachments
                FROM scheduled_emails
                WHERE send_at <= now() AND status = 'pending'
                ORDER BY send_at ASC
                """
            )
        )
        items = result.mappings().all()

        for item in items:
            mailbox_row = await session.execute(
                text("SELECT * FROM mailboxes WHERE id = :mailbox_id"),
                {"mailbox_id": str(item["mailbox_id"])},
            )
            mailbox = mailbox_row.mappings().first()
            if mailbox is None:
                await session.execute(
                    text("UPDATE scheduled_emails SET status='failed', error_message=:err WHERE id = :id"),
                    {"id": str(item["id"]), "err": "Mailbox not found"},
                )
                continue

            class MailboxProxy:
                id = mailbox["id"]
                full_address = mailbox["full_address"]

            payload = {
                "to": list(item["to_addresses"] or []),
                "cc": list(item["cc_addresses"] or []),
                "bcc": list(item["bcc_addresses"] or []),
                "subject": item["subject"],
                "body_text": item["body_text"] or "",
                "body_html": item["body_html"],
                "attachments": item["attachments"] or [],
            }

            try:
                await MailService.send_email(session, MailboxProxy(), payload)
                await session.execute(
                    text("UPDATE scheduled_emails SET status='sent', error_message=NULL WHERE id = :id"),
                    {"id": str(item["id"])},
                )
            except Exception as exc:
                await session.execute(
                    text("UPDATE scheduled_emails SET status='failed', error_message=:err WHERE id = :id"),
                    {"id": str(item["id"]), "err": str(exc)},
                )

        await session.commit()


@celery_app.task(name="tasks.scheduled_email_tasks.process_scheduled_emails")
def process_scheduled_emails() -> None:
    asyncio.run(_process())
