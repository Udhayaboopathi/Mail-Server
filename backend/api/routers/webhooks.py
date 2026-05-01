from __future__ import annotations

import hashlib
import hmac
import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_user_mailbox
from schemas.webhooks import WebhookCreateRequest, WebhookResponse, WebhookUpdateRequest

router = APIRouter(tags=["webhooks"])


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> list[WebhookResponse]:
    result = await db.execute(
        text("SELECT * FROM webhooks WHERE mailbox_id = :mailbox_id ORDER BY created_at DESC"),
        {"mailbox_id": str(mailbox.id)},
    )
    return [WebhookResponse(**row) for row in result.mappings().all()]


@router.post("", response_model=WebhookResponse)
async def create_webhook(payload: WebhookCreateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> WebhookResponse:
    result = await db.execute(
        text(
            """
            INSERT INTO webhooks (mailbox_id, url, secret, events, is_active, created_at)
            VALUES (:mailbox_id, :url, :secret, :events, true, now())
            RETURNING *
            """
        ),
        {
            "mailbox_id": str(mailbox.id),
            "url": payload.url,
            "secret": payload.secret,
            "events": payload.events,
        },
    )
    row = result.mappings().first()
    await db.commit()
    return WebhookResponse(**row)


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(webhook_id: str, payload: WebhookUpdateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> WebhookResponse:
    result = await db.execute(
        text(
            """
            UPDATE webhooks
            SET url = COALESCE(:url, url),
                secret = COALESCE(:secret, secret),
                events = COALESCE(:events, events),
                is_active = COALESCE(:is_active, is_active)
            WHERE id = :id AND mailbox_id = :mailbox_id
            RETURNING *
            """
        ),
        {
            "id": webhook_id,
            "mailbox_id": str(mailbox.id),
            "url": payload.url,
            "secret": payload.secret,
            "events": payload.events,
            "is_active": payload.is_active,
        },
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    await db.commit()
    return WebhookResponse(**row)


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text("DELETE FROM webhooks WHERE id = :id AND mailbox_id = :mailbox_id"),
        {"id": webhook_id, "mailbox_id": str(mailbox.id)},
    )
    await db.commit()
    return {"status": "deleted"}


@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text("SELECT url, secret FROM webhooks WHERE id = :id AND mailbox_id = :mailbox_id"),
        {"id": webhook_id, "mailbox_id": str(mailbox.id)},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    payload = {"event": "test", "mailbox_id": str(mailbox.id)}
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(str(row["secret"]).encode("utf-8"), body, hashlib.sha256).hexdigest()

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            str(row["url"]),
            content=body,
            headers={"Content-Type": "application/json", "X-Webhook-Sig": signature},
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Webhook test failed")

    return {"status": "sent"}
