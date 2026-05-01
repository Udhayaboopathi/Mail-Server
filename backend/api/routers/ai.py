from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from database import get_db
from deps import get_current_user, get_user_mailbox
from imap.maildir import MaildirBackend
from schemas.ai import AiPriorityInboxResponse, AiSmartReplyRequest, AiSmartReplyResponse, AiSuggestLabelsRequest, AiSuggestLabelsResponse, AiSummarizeRequest, AiSummarizeResponse
from services.ai_service import rank_emails_by_priority, smart_reply_suggestions, suggest_labels, summarize_thread
from services.thread_service import get_thread_messages
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

router = APIRouter(tags=["ai"])

_backend = MaildirBackend()


@router.post("/summarize", response_model=AiSummarizeResponse)
async def summarize(payload: AiSummarizeRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> AiSummarizeResponse:
    messages = payload.messages
    if payload.thread_id:
        thread_messages = await get_thread_messages(payload.thread_id, str(mailbox.id), db)
        messages = [
            {
                "from": item.get("from"),
                "subject": item.get("subject"),
                "body": item.get("preview"),
                "date": item.get("date"),
            }
            for item in thread_messages
        ]
    summary = await summarize_thread(messages or [])
    return AiSummarizeResponse(summary=summary)


@router.post("/smart-reply", response_model=AiSmartReplyResponse)
async def smart_reply(payload: AiSmartReplyRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> AiSmartReplyResponse:
    thread_messages = await get_thread_messages(payload.thread_id, str(mailbox.id), db)
    suggestions = await smart_reply_suggestions(
        [
            {
                "from": item.get("from"),
                "subject": item.get("subject"),
                "body": item.get("preview"),
                "date": item.get("date"),
            }
            for item in thread_messages
        ]
    )
    return AiSmartReplyResponse(suggestions=suggestions)


@router.get("/priority-inbox", response_model=AiPriorityInboxResponse)
async def priority_inbox(mailbox=Depends(get_user_mailbox)) -> AiPriorityInboxResponse:
    items = _backend.list_messages(str(mailbox.id), "Inbox")[:100]
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
    return AiPriorityInboxResponse(emails=ranked)


@router.post("/suggest-labels", response_model=AiSuggestLabelsResponse)
async def suggest_labels_route(payload: AiSuggestLabelsRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> AiSuggestLabelsResponse:
    msg = _backend.read_message(str(mailbox.id), "Inbox", payload.email_uid)
    if msg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    labels = await db.execute(
        text("SELECT name FROM labels WHERE mailbox_id = :mailbox_id"),
        {"mailbox_id": str(mailbox.id)},
    )
    existing = [row["name"] for row in labels.mappings().all()]
    suggestions = await suggest_labels(
        {"from": msg.get("From", ""), "subject": msg.get("Subject", ""), "body": msg.get_payload()},
        existing,
    )
    return AiSuggestLabelsResponse(suggestions=suggestions)
