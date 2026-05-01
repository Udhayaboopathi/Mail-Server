from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from urllib.parse import quote

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings


def generate_tracking_pixel_html(read_receipt_id: str, token: str) -> str:
    return (
        f"<img src=\"{settings.tracking_base_url}/px/{token}.gif\" "
        "width=\"1\" height=\"1\" style=\"display:none\" alt=\"\" />"
    )


async def wrap_links_for_tracking(body_html: str, read_receipt_id: str, db: AsyncSession) -> str:
    if not body_html:
        return body_html

    links: list[tuple[str, str]] = []

    def _replace(match: re.Match[str]) -> str:
        original = match.group("url")
        lower = original.lower()
        if lower.startswith("mailto:") or lower.startswith("javascript:") or original.startswith("#"):
            return match.group(0)
        token = secrets.token_hex(16)
        links.append((original, token))
        encoded = quote(original, safe="")
        tracked = f"{settings.tracking_base_url}/click/{token}?url={encoded}"
        return match.group(0).replace(original, tracked)

    updated_html = re.sub(r"<a\s+[^>]*href=[\"'](?P<url>[^\"']+)[\"'][^>]*>", _replace, body_html, flags=re.IGNORECASE)

    if links:
        for original, token in links:
            await db.execute(
                text(
                    """
                    INSERT INTO email_link_clicks (read_receipt_id, original_url, tracking_token)
                    VALUES (:read_receipt_id, :original_url, :tracking_token)
                    """
                ),
                {
                    "read_receipt_id": read_receipt_id,
                    "original_url": original,
                    "tracking_token": token,
                },
            )
        await db.commit()

    return updated_html


async def generate_unsubscribe_token(sender_mailbox_id: str, recipient_email: str, db: AsyncSession) -> str:
    token = secrets.token_hex(32)
    await db.execute(
        text(
            """
            INSERT INTO unsubscribe_tokens (sender_mailbox_id, recipient_email, token, created_at)
            VALUES (:sender_mailbox_id, :recipient_email, :token, now())
            ON CONFLICT (sender_mailbox_id, recipient_email)
            DO UPDATE SET token = EXCLUDED.token, unsubscribed_at = NULL, created_at = now()
            """
        ),
        {
            "sender_mailbox_id": sender_mailbox_id,
            "recipient_email": recipient_email,
            "token": token,
        },
    )
    await db.commit()
    return token


def add_unsubscribe_header(body_html: str, token: str) -> str:
    footer = f'<p><a href="{settings.frontend_url}/unsubscribe/{token}">Unsubscribe</a></p>'
    return (body_html or "") + footer


async def fire_webhook(mailbox_id: str, event: str, payload: dict, db: AsyncSession) -> None:
    result = await db.execute(
        text(
            """
            SELECT id, url, secret, failure_count
            FROM webhooks
            WHERE mailbox_id = :mailbox_id
              AND is_active = true
              AND :event = ANY(events)
            """
        ),
        {"mailbox_id": mailbox_id, "event": event},
    )
    rows = result.mappings().all()
    if not rows:
        return

    body = json.dumps(payload).encode("utf-8")

    async with httpx.AsyncClient(timeout=10.0) as client:
        for row in rows:
            signature = hmac.new(str(row["secret"]).encode("utf-8"), body, hashlib.sha256).hexdigest()
            try:
                response = await client.post(
                    str(row["url"]),
                    content=body,
                    headers={"Content-Type": "application/json", "X-Webhook-Sig": signature},
                )
                if response.status_code >= 400:
                    raise httpx.HTTPStatusError("bad status", request=response.request, response=response)
                await db.execute(
                    text(
                        """
                        UPDATE webhooks
                        SET last_triggered_at = now(), failure_count = 0
                        WHERE id = :id
                        """
                    ),
                    {"id": str(row["id"])},
                )
            except Exception:
                await db.execute(
                    text(
                        """
                        UPDATE webhooks
                        SET failure_count = failure_count + 1,
                            is_active = CASE WHEN failure_count + 1 >= 10 THEN false ELSE true END
                        WHERE id = :id
                        """
                    ),
                    {"id": str(row["id"])},
                )
        await db.commit()
