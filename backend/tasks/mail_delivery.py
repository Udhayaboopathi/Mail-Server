import asyncio

from celery import shared_task

from services.mail_service import MailService


@shared_task(name="tasks.mail_delivery.enqueue_delivery", bind=True, max_retries=5)
def enqueue_delivery(self, raw_message: str) -> str:
    async def _send() -> str:
        return "queued"

    asyncio.run(_send())
    return "queued"
