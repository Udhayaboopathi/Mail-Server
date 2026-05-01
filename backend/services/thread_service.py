from __future__ import annotations

from email import message_from_bytes
from email.policy import default
from email.utils import parsedate_to_datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from imap.maildir import MaildirBackend


_backend = MaildirBackend()


def _normalize_subject(subject: str) -> str:
    cleaned = subject or ""
    prefixes = ("re:", "fwd:", "fw:")
    while True:
        lowered = cleaned.strip().lower()
        if any(lowered.startswith(prefix) for prefix in prefixes):
            parts = cleaned.split(":", 1)
            cleaned = parts[1] if len(parts) > 1 else cleaned
            continue
        break
    return cleaned.strip()


def _preview_from_message(raw: bytes) -> str:
    msg = message_from_bytes(raw, policy=default)
    body = msg.get_body(preferencelist=("plain",))
    if body:
        return body.get_content().strip()[:120]
    payload = msg.get_payload()
    if isinstance(payload, str):
        return payload.strip()[:120]
    return ""


async def get_or_create_thread(
    mailbox_id: str,
    message_id: str | None,
    in_reply_to: str | None,
    subject: str,
    db: AsyncSession,
) -> str:
    normalized = _normalize_subject(subject)
    result = await db.execute(
        text(
            """
            SELECT id
            FROM email_threads
            WHERE mailbox_id = :mailbox_id
              AND subject = :subject
            LIMIT 1
            """
        ),
        {"mailbox_id": mailbox_id, "subject": normalized},
    )
    row = result.mappings().first()
    if row:
        await db.execute(
            text(
                """
                UPDATE email_threads
                SET last_message_at = now(), message_count = message_count + 1, has_unread = true
                WHERE id = :thread_id
                """
            ),
            {"thread_id": str(row["id"])},
        )
        await db.commit()
        return str(row["id"])

    insert = await db.execute(
        text(
            """
            INSERT INTO email_threads (mailbox_id, subject, participants, last_message_at, message_count, has_unread, created_at)
            VALUES (:mailbox_id, :subject, :participants, now(), 1, true, now())
            RETURNING id
            """
        ),
        {"mailbox_id": mailbox_id, "subject": normalized, "participants": []},
    )
    new_row = insert.mappings().first()
    await db.commit()
    return str(new_row["id"])


async def get_thread_messages(thread_id: str, mailbox_id: str, db: AsyncSession) -> list:
    thread_row = await db.execute(
        text("SELECT subject FROM email_threads WHERE id = :thread_id AND mailbox_id = :mailbox_id"),
        {"thread_id": thread_id, "mailbox_id": mailbox_id},
    )
    thread = thread_row.mappings().first()
    if not thread:
        return []

    target_subject = _normalize_subject(str(thread["subject"]))
    messages: list[dict[str, Any]] = []

    for folder in _backend.list_folders(mailbox_id):
        for item in _backend.list_messages(mailbox_id, folder):
            subject = _normalize_subject(str(item.get("subject", "")))
            if subject != target_subject:
                continue
            raw = item.get("raw")
            preview = _preview_from_message(raw) if raw else ""
            date_value = item.get("date")
            parsed_date = None
            if date_value:
                try:
                    parsed_date = parsedate_to_datetime(str(date_value))
                except Exception:
                    parsed_date = None
            messages.append(
                {
                    "uid": item.get("uid"),
                    "folder": folder,
                    "from": item.get("from"),
                    "to": item.get("to"),
                    "subject": item.get("subject"),
                    "date": parsed_date,
                    "flags": item.get("flags", []),
                    "preview": preview,
                }
            )

    messages.sort(key=lambda x: x.get("date") or 0)
    return messages
