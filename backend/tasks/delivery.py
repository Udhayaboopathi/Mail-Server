from __future__ import annotations

import asyncio
from email.message import EmailMessage
from typing import Any

from celery import shared_task

from smtp.outbound import deliver_outbound


async def _deliver(payload: dict[str, Any]) -> str:
    message = EmailMessage()
    message["From"] = payload["from"]
    message["To"] = payload["to"]
    message["Subject"] = payload.get("subject", "")
    message.set_content(payload.get("body_text", ""))
    if payload.get("body_html"):
        message.add_alternative(payload["body_html"], subtype="html")
    await deliver_outbound(message, payload["to"])
    return "sent"


@shared_task(name="tasks.delivery.queue_delivery", bind=True, max_retries=5)
def queue_delivery(self, payload: dict[str, Any]) -> str:
    try:
        return asyncio.run(_deliver(payload))
    except Exception as exc:  # pragma: no cover - retry path
        raise self.retry(exc=exc, countdown=min(300, 2 ** self.request.retries))
