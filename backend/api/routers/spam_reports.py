from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_user_mailbox
from imap.maildir import MaildirBackend
from schemas.spam_reports import SpamReportRequest, SpamReportResponse

router = APIRouter(tags=["spam-reports"])

_backend = MaildirBackend()


async def _train_spam(action: str, raw_message: bytes) -> None:
    cmd = ["spamc", "--report"] if action == "spam" else ["spamc", "--revoke"]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await process.communicate(raw_message)


@router.post("/spam", response_model=SpamReportResponse)
async def report_spam(payload: SpamReportRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> SpamReportResponse:
    message = _backend.read_message(str(mailbox.id), "Inbox", int(payload.email_uid))
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    raw = message.as_bytes()
    await _train_spam("spam", raw)
    _backend.move(str(mailbox.id), "Inbox", "Spam", int(payload.email_uid))

    await db.execute(
        text(
            """
            INSERT INTO spam_reports (mailbox_id, email_uid, from_address, report_type, created_at)
            VALUES (:mailbox_id, :email_uid, :from_address, 'spam', now())
            """
        ),
        {
            "mailbox_id": str(mailbox.id),
            "email_uid": str(payload.email_uid),
            "from_address": payload.from_address,
        },
    )
    await db.commit()
    return SpamReportResponse(status="reported")


@router.post("/not-spam", response_model=SpamReportResponse)
async def report_not_spam(payload: SpamReportRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> SpamReportResponse:
    message = _backend.read_message(str(mailbox.id), "Spam", int(payload.email_uid))
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    raw = message.as_bytes()
    await _train_spam("not_spam", raw)
    _backend.move(str(mailbox.id), "Spam", "Inbox", int(payload.email_uid))

    await db.execute(
        text(
            """
            INSERT INTO spam_reports (mailbox_id, email_uid, from_address, report_type, created_at)
            VALUES (:mailbox_id, :email_uid, :from_address, 'not_spam', now())
            """
        ),
        {
            "mailbox_id": str(mailbox.id),
            "email_uid": str(payload.email_uid),
            "from_address": payload.from_address,
        },
    )
    await db.commit()
    return SpamReportResponse(status="reported")
