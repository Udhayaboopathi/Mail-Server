from __future__ import annotations

import asyncio
from dataclasses import dataclass

from aiosmtpd.controller import Controller

from config import settings
from smtp.handler import SMTPHandler
from smtp.tls import create_tls_context


@dataclass
class SMTPServerBundle:
    inbound: Controller
    submission: Controller

    def close(self) -> None:
        self.inbound.stop()
        self.submission.stop()

    async def wait_closed(self) -> None:
        await asyncio.sleep(0)


async def create_smtp_server() -> SMTPServerBundle:
    handler = SMTPHandler()
    tls_context = create_tls_context()
    inbound = Controller(handler, hostname="0.0.0.0", port=25, ready_timeout=5.0)
    submission = Controller(handler, hostname="0.0.0.0", port=587, tls_context=tls_context, ready_timeout=5.0)
    await asyncio.to_thread(inbound.start)
    await asyncio.to_thread(submission.start)
    return SMTPServerBundle(inbound=inbound, submission=submission)
