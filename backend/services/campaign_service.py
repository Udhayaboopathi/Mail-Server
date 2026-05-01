from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import make_msgid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from smtp.outbound import deliver_outbound
from services.tracking_service import add_unsubscribe_header, generate_tracking_pixel_html, generate_unsubscribe_token, wrap_links_for_tracking


def _load_recipients(raw: object) -> list[dict]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []
    return []


def _personalize(template: str, recipient: dict) -> str:
    if not template:
        return ""
    result = template.replace("{{name}}", str(recipient.get("name", "")))
    result = result.replace("{{email}}", str(recipient.get("email", "")))
    variables = recipient.get("vars") or {}
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


async def send_campaign(campaign_id: str, db: AsyncSession) -> None:
    result = await db.execute(text("SELECT * FROM campaign_emails WHERE id = :id"), {"id": campaign_id})
    campaign = result.mappings().first()
    if campaign is None:
        raise ValueError("Campaign not found")

    recipients = _load_recipients(campaign.get("recipients"))
    await db.execute(
        text(
            """
            UPDATE campaign_emails
            SET status = 'sending', started_at = now(), total_recipients = :total
            WHERE id = :id
            """
        ),
        {"id": campaign_id, "total": len(recipients)},
    )
    await db.commit()

    mailbox_row = await db.execute(
        text("SELECT full_address FROM mailboxes WHERE id = :mailbox_id"),
        {"mailbox_id": str(campaign["mailbox_id"])},
    )
    mailbox = mailbox_row.mappings().first()
    if mailbox is None:
        raise ValueError("Mailbox not found")

    sent_count = 0
    failed_count = 0
    unsubscribe_count = 0

    for recipient in recipients:
        email = str(recipient.get("email", "")).strip().lower()
        if not email:
            failed_count += 1
            continue

        unsub = await db.execute(
            text(
                """
                SELECT 1
                FROM unsubscribe_list
                WHERE sender_mailbox_id = :mailbox_id AND recipient_email = :recipient
                LIMIT 1
                """
            ),
            {"mailbox_id": str(campaign["mailbox_id"]), "recipient": email},
        )
        if unsub.first() is not None:
            unsubscribe_count += 1
            continue

        subject = _personalize(str(campaign["subject"]), recipient)
        body_html = _personalize(str(campaign["body_html"]), recipient)
        body_text = _personalize(str(campaign.get("body_text") or ""), recipient)

        message_id = f"campaign-{campaign_id}-{secrets.token_hex(8)}"
        read_receipt_id = None
        if settings.tracking_enabled:
            receipt = await db.execute(
                text(
                    """
                    INSERT INTO read_receipts (sender_mailbox_id, message_id, recipient_email, created_at)
                    VALUES (:sender_mailbox_id, :message_id, :recipient_email, now())
                    RETURNING id
                    """
                ),
                {
                    "sender_mailbox_id": str(campaign["mailbox_id"]),
                    "message_id": message_id,
                    "recipient_email": email,
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
            body_html += generate_tracking_pixel_html(str(read_receipt_id), token)

        if read_receipt_id:
            body_html = await wrap_links_for_tracking(body_html, str(read_receipt_id), db)

        unsubscribe_token = await generate_unsubscribe_token(str(campaign["mailbox_id"]), email, db)
        body_html = add_unsubscribe_header(body_html, unsubscribe_token)

        message = EmailMessage()
        from_address = str(mailbox["full_address"])
        from_name = campaign.get("from_name")
        message["From"] = f"{from_name} <{from_address}>" if from_name else from_address
        message["To"] = email
        message["Subject"] = subject
        message["Message-ID"] = message_id
        if body_text:
            message.set_content(body_text)
        if body_html:
            message.add_alternative(body_html, subtype="html")

        try:
            await deliver_outbound(message, email, str(campaign["mailbox_id"]))
            sent_count += 1
        except Exception:
            failed_count += 1

    status = "sent"
    if sent_count == 0 and failed_count > 0:
        status = "failed"

    await db.execute(
        text(
            """
            UPDATE campaign_emails
            SET status = :status,
                completed_at = now(),
                sent_count = :sent_count,
                failed_count = :failed_count,
                unsubscribe_count = :unsubscribe_count
            WHERE id = :id
            """
        ),
        {
            "id": campaign_id,
            "status": status,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "unsubscribe_count": unsubscribe_count,
        },
    )
    await db.commit()


async def get_campaign_analytics(campaign_id: str, db: AsyncSession) -> dict:
    result = await db.execute(
        text(
            """
            SELECT sent_count, failed_count, open_count, click_count, unsubscribe_count, mailbox_id
            FROM campaign_emails
            WHERE id = :id
            """
        ),
        {"id": campaign_id},
    )
    campaign = result.mappings().first()
    if campaign is None:
        raise ValueError("Campaign not found")

    prefix = f"campaign-{campaign_id}-%"
    opens = await db.execute(
        text(
            """
            SELECT COUNT(*) AS opens, COUNT(DISTINCT recipient_email) AS unique_opens
            FROM read_receipts
            WHERE message_id LIKE :prefix
            """
        ),
        {"prefix": prefix},
    )
    open_row = opens.mappings().first()

    clicks = await db.execute(
        text(
            """
            SELECT COUNT(*) AS clicks, COUNT(DISTINCT r.recipient_email) AS unique_clicks
            FROM email_link_clicks c
            JOIN read_receipts r ON r.id = c.read_receipt_id
            WHERE r.message_id LIKE :prefix
            """
        ),
        {"prefix": prefix},
    )
    click_row = clicks.mappings().first()

    sent = int(campaign["sent_count"] or 0)
    open_count = int(open_row["opens"] or 0)
    click_count = int(click_row["clicks"] or 0)
    unique_opens = int(open_row["unique_opens"] or 0)
    unique_clicks = int(click_row["unique_clicks"] or 0)
    open_rate = (open_count / sent) * 100 if sent else 0
    click_rate = (click_count / sent) * 100 if sent else 0

    return {
        "sent": sent,
        "opens": open_count,
        "unique_opens": unique_opens,
        "clicks": click_count,
        "unique_clicks": unique_clicks,
        "unsubscribes": int(campaign["unsubscribe_count"] or 0),
        "open_rate": open_rate,
        "click_rate": click_rate,
    }
