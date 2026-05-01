from __future__ import annotations

import asyncio
from email.message import EmailMessage

import aiosmtplib
import dns.resolver

from config import settings
from smtp.dkim import sign_message


async def resolve_mx(domain: str) -> list[str]:
    answers = dns.resolver.resolve(domain, "MX")
    return [str(answer.exchange).rstrip(".") for answer in answers]


async def deliver_outbound(message: EmailMessage, recipient: str) -> None:
    signed = await sign_message(message.as_bytes(), recipient.split("@", 1)[1])
    mx_hosts = await resolve_mx(recipient.split("@", 1)[1])
    last_error: Exception | None = None

    for host in mx_hosts:
        try:
            client = aiosmtplib.SMTP(hostname=host, port=25, timeout=20)
            await client.connect()
            await client.sendmail(message["From"], [recipient], signed)
            await client.quit()
            return
        except Exception as exc:  # pragma: no cover - external network failure path
            last_error = exc
            await asyncio.sleep(1)

    if last_error is not None:
        raise last_error
