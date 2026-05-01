from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from imap.maildir import MaildirBackend
from models.mailbox import Mailbox
from tasks.delivery import queue_delivery


class MailService:
    backend = MaildirBackend()

    @staticmethod
    async def send_email(session: AsyncSession, sender: Mailbox, payload: dict[str, object]) -> dict[str, str]:
        message = EmailMessage()
        message["From"] = sender.full_address
        message["To"] = ", ".join(payload["to"])
        if payload.get("cc"):
            message["Cc"] = ", ".join(payload["cc"])
        message["Subject"] = str(payload["subject"])
        message.set_content(str(payload["body_text"]))
        if payload.get("body_html"):
            message.add_alternative(str(payload["body_html"]), subtype="html")
        try:
            client = aiosmtplib.SMTP(hostname="127.0.0.1", port=587, timeout=20)
            await client.connect()
            await client.send_message(message)
            await client.quit()
            return {"status": "sent"}
        except Exception:
            queue_delivery.delay({"from": sender.full_address, "to": payload["to"][0], "subject": str(payload["subject"]), "body_text": str(payload["body_text"]), "body_html": payload.get("body_html")})
            return {"status": "queued"}

    @staticmethod
    async def list_messages(mailbox_id: str, folder: str, page: int = 1, limit: int = 50) -> list[dict[str, object]]:
        messages = MailService.backend.list_messages(mailbox_id, folder)
        start = (page - 1) * limit
        selected = messages[start : start + limit]
        return [
            {
                "id": str(item["uid"]),
                "uid": int(item["uid"]),
                "sender": str(item["from"]),
                "recipients": [str(item["to"])],
                "subject": str(item["subject"]),
                "date": None,
                "flags": list(item["flags"]),
                "size": int(item["size"]),
                "has_attachments": False,
                "preview": "",
            }
            for item in selected
        ]

    @staticmethod
    async def get_message(mailbox_id: str, folder: str, uid: int) -> dict[str, object] | None:
        message = MailService.backend.read_message(mailbox_id, folder, uid)
        if message is None:
            return None
        raw = message.as_string()
        return {
            "id": str(uid),
            "uid": uid,
            "folder": folder,
            "headers": {"from": message.get("From", ""), "to": message.get("To", ""), "subject": message.get("Subject", ""), "date": message.get("Date", "")},
            "body_text": str(message.get_payload()),
            "body_html": None,
            "attachments": [],
            "flags": [],
            "date": None,
        }
