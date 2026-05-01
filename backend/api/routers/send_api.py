from __future__ import annotations

import secrets
from datetime import datetime, timezone

import bcrypt
import redis.asyncio as redis
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from schemas.send_api import SendApiRequest, SendApiResponse
from services.tracking_service import generate_tracking_pixel_html, wrap_links_for_tracking
from tasks.delivery import queue_delivery

router = APIRouter(tags=["send-api"])


@router.post("/send", response_model=SendApiResponse)
async def send_via_api(
    payload: SendApiRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> SendApiResponse:
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    prefix = api_key[:8]
    result = await db.execute(
        text(
            """
            SELECT *
            FROM api_keys
            WHERE key_prefix = :prefix AND is_active = true
            """
        ),
        {"prefix": prefix},
    )
    rows = result.mappings().all()
    api_row = None
    for row in rows:
        if bcrypt.checkpw(api_key.encode("utf-8"), str(row["key_hash"]).encode("utf-8")):
            api_row = row
            break

    if api_row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    if api_row.get("expires_at") and api_row["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    scopes = api_row.get("scopes") or []
    if "send" not in scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing send scope")

    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    bucket = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    rate_key = f"api_key:{api_row['id']}:{bucket}"
    count = await redis_client.incr(rate_key)
    if count == 1:
        await redis_client.expire(rate_key, 3600)
    if count > int(api_row.get("rate_limit_per_hour") or 1000):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    all_recipients = list({*(payload.to or []), *(payload.cc or []), *(payload.bcc or [])})
    if not all_recipients:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No recipients")

    mailbox_row = await db.execute(
        text("SELECT full_address FROM mailboxes WHERE id = :id"),
        {"id": str(api_row["mailbox_id"])},
    )
    mailbox = mailbox_row.mappings().first()
    if mailbox is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mailbox not found")
    from_address = str(mailbox["full_address"])
    from_value = f"{payload.from_name} <{from_address}>" if payload.from_name else from_address

    for recipient in all_recipients:
        unsub = await db.execute(
            text(
                """
                SELECT 1 FROM unsubscribe_list
                WHERE sender_mailbox_id = :mailbox_id AND recipient_email = :recipient
                LIMIT 1
                """
            ),
            {"mailbox_id": str(api_row["mailbox_id"]), "recipient": recipient.lower()},
        )
        if unsub.first() is not None:
            continue

        body_html = payload.html or ""
        if (payload.track_opens or payload.track_clicks) and settings.tracking_enabled:
            message_id = f"api-{api_row['id']}-{secrets.token_hex(8)}"
            receipt = await db.execute(
                text(
                    """
                    INSERT INTO read_receipts (sender_mailbox_id, message_id, recipient_email, created_at)
                    VALUES (:sender_mailbox_id, :message_id, :recipient_email, now())
                    RETURNING id
                    """
                ),
                {
                    "sender_mailbox_id": str(api_row["mailbox_id"]),
                    "message_id": message_id,
                    "recipient_email": recipient.lower(),
                },
            )
            read_receipt_id = receipt.mappings().first()["id"]
            token = secrets.token_hex(16)
            await db.execute(
                text(
                    """
                    INSERT INTO email_tracking_pixels (read_receipt_id, token, created_at)
                    VALUES (:read_receipt_id, :token, now())
                    """
                ),
                {"read_receipt_id": str(read_receipt_id), "token": token},
            )
            if payload.track_opens:
                body_html += generate_tracking_pixel_html(str(read_receipt_id), token)
            if payload.track_clicks:
                body_html = await wrap_links_for_tracking(body_html, str(read_receipt_id), db)
            await db.commit()

        queue_delivery.delay(
            {
                "from": from_value,
                "to": recipient,
                "subject": payload.subject,
                "body_text": payload.text or "",
                "body_html": body_html or None,
                "mailbox_id": str(api_row["mailbox_id"]),
            }
        )

    await db.execute(
        text("UPDATE api_keys SET last_used_at = now() WHERE id = :id"), {"id": str(api_row["id"])}
    )
    await db.commit()

    return SendApiResponse(message_id=f"api-{api_row['id']}-{secrets.token_hex(6)}", queued=True)
