from __future__ import annotations

import io
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

router = APIRouter(tags=["tracking"])


def _pixel_bytes() -> bytes:
    image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="GIF")
    return buffer.getvalue()


@router.get("/px/{token}.gif")
async def tracking_pixel(token: str, request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(
        text(
            """
            SELECT tp.read_receipt_id, rr.message_id
            FROM email_tracking_pixels tp
            JOIN read_receipts rr ON rr.id = tp.read_receipt_id
            WHERE tp.token = :token
            """
        ),
        {"token": token},
    )
    row = result.mappings().first()
    if row:
        await db.execute(
            text(
                """
                UPDATE read_receipts
                SET opened_at = COALESCE(opened_at, now()),
                    open_count = open_count + 1,
                    ip_address = :ip,
                    user_agent = :ua
                WHERE id = :id
                """
            ),
            {
                "id": str(row["read_receipt_id"]),
                "ip": request.client.host if request.client else None,
                "ua": request.headers.get("user-agent"),
            },
        )
        match = re.match(r"campaign-([a-f0-9-]+)-", str(row["message_id"]))
        if match:
            await db.execute(
                text("UPDATE campaign_emails SET open_count = open_count + 1 WHERE id = :id"),
                {"id": match.group(1)},
            )
        await db.commit()

    return Response(_pixel_bytes(), media_type="image/gif")


@router.get("/click/{token}")
async def track_click(token: str, url: str, db: AsyncSession = Depends(get_db)) -> RedirectResponse:
    result = await db.execute(
        text(
            """
            SELECT c.id, r.message_id
            FROM email_link_clicks c
            JOIN read_receipts r ON r.id = c.read_receipt_id
            WHERE c.tracking_token = :token
            """
        ),
        {"token": token},
    )
    row = result.mappings().first()
    if row:
        await db.execute(
            text(
                """
                UPDATE email_link_clicks
                SET click_count = click_count + 1,
                    first_clicked_at = COALESCE(first_clicked_at, now()),
                    last_clicked_at = now()
                WHERE id = :id
                """
            ),
            {"id": str(row["id"])},
        )
        match = re.match(r"campaign-([a-f0-9-]+)-", str(row["message_id"]))
        if match:
            await db.execute(
                text("UPDATE campaign_emails SET click_count = click_count + 1 WHERE id = :id"),
                {"id": match.group(1)},
            )
        await db.commit()

    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get("/unsubscribe/{token}")
async def unsubscribe(token: str, db: AsyncSession = Depends(get_db)) -> HTMLResponse:
    result = await db.execute(
        text(
            """
            SELECT sender_mailbox_id, recipient_email
            FROM unsubscribe_tokens
            WHERE token = :token
            """
        ),
        {"token": token},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid token")

    await db.execute(
        text(
            """
            UPDATE unsubscribe_tokens
            SET unsubscribed_at = now()
            WHERE token = :token
            """
        ),
        {"token": token},
    )
    await db.execute(
        text(
            """
            INSERT INTO unsubscribe_list (sender_mailbox_id, recipient_email, unsubscribed_at)
            VALUES (:sender_mailbox_id, :recipient_email, now())
            ON CONFLICT (sender_mailbox_id, recipient_email) DO NOTHING
            """
        ),
        {"sender_mailbox_id": str(row["sender_mailbox_id"]), "recipient_email": row["recipient_email"]},
    )
    await db.commit()

    html = "<html><body><h2>You have been unsubscribed.</h2></body></html>"
    return HTMLResponse(content=html)
