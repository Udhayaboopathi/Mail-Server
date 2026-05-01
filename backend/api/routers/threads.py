from __future__ import annotations

from email import message_from_bytes
from email.policy import default
from email.utils import parsedate_to_datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_user_mailbox
from imap.maildir import MaildirBackend
from schemas.threads import ThreadMessage, ThreadSummary
from services.thread_service import get_thread_messages

router = APIRouter(tags=["threads"])

_backend = MaildirBackend()


def _preview(raw: bytes | None) -> str:
    if not raw:
        return ""
    msg = message_from_bytes(raw, policy=default)
    body = msg.get_body(preferencelist=("plain",))
    if body:
        return body.get_content().strip()[:160]
    payload = msg.get_payload()
    if isinstance(payload, str):
        return payload.strip()[:160]
    return ""


def _normalize_subject(subject: str) -> str:
    cleaned = subject or ""
    while True:
        lower = cleaned.strip().lower()
        if lower.startswith("re:") or lower.startswith("fwd:") or lower.startswith("fw:"):
            cleaned = cleaned.split(":", 1)[1] if ":" in cleaned else cleaned
            continue
        break
    return cleaned.strip()


@router.get("/threads/{folder}", response_model=list[ThreadSummary])
async def list_threads(
    folder: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    mailbox=Depends(get_user_mailbox),
    db: AsyncSession = Depends(get_db),
) -> list[ThreadSummary]:
    result = await db.execute(
        text(
            """
            SELECT *
            FROM email_threads
            WHERE mailbox_id = :mailbox_id
            ORDER BY last_message_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"mailbox_id": str(mailbox.id), "limit": limit, "offset": (page - 1) * limit},
    )
    threads = []
    for row in result.mappings().all():
        normalized = _normalize_subject(str(row["subject"]))
        latest_preview = ""
        last_sender = ""
        last_date = row.get("last_message_at")
        labels = []
        for item in _backend.list_messages(str(mailbox.id), folder):
            if _normalize_subject(str(item.get("subject", ""))) != normalized:
                continue
            latest_preview = _preview(item.get("raw"))
            last_sender = str(item.get("from", ""))
            try:
                parsed = parsedate_to_datetime(str(item.get("date"))) if item.get("date") else None
            except Exception:
                parsed = None
            if parsed:
                last_date = parsed
            label_rows = await db.execute(
                text(
                    """
                    SELECT l.name, l.color
                    FROM email_labels el
                    JOIN labels l ON l.id = el.label_id
                    WHERE el.mailbox_id = :mailbox_id AND el.email_uid = :email_uid
                    """
                ),
                {"mailbox_id": str(mailbox.id), "email_uid": str(item.get("uid"))},
            )
            labels = [dict(label) for label in label_rows.mappings().all()]
            break

        threads.append(
            ThreadSummary(
                thread_id=str(row["id"]),
                subject=str(row["subject"]),
                participants=row.get("participants") or [],
                last_message_at=last_date,
                message_count=int(row.get("message_count") or 0),
                has_unread=bool(row.get("has_unread")),
                latest_preview=latest_preview,
                labels=labels,
                last_sender=last_sender,
            )
        )
    return threads


@router.get("/threads/{thread_id}/messages", response_model=list[ThreadMessage])
async def thread_messages(thread_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> list[ThreadMessage]:
    items = await get_thread_messages(thread_id, str(mailbox.id), db)
    return [ThreadMessage(**item) for item in items]
