from __future__ import annotations

import asyncio
from email.message import EmailMessage
from email.utils import make_msgid

import aiosmtplib
import dns.resolver
from cryptography.fernet import Fernet
from pgpy import PGPKey, PGPMessage
from pgpy.constants import HashAlgorithm
from sqlalchemy import text

from config import settings
from database import AsyncSessionLocal
from smtp.dkim import sign_message
from services.tracking_service import fire_webhook


async def resolve_mx(domain: str) -> list[str]:
    answers = dns.resolver.resolve(domain, "MX")
    return [str(answer.exchange).rstrip(".") for answer in answers]


def _get_body(message: EmailMessage) -> tuple[str, str]:
    if message.is_multipart():
        plain = ""
        html = ""
        for part in message.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                plain = part.get_content()
            if ctype == "text/html":
                html = part.get_content()
        return plain, html
    return message.get_content(), ""


def _set_single_body(message: EmailMessage, body_text: str) -> None:
    message.clear_content()
    message.set_content(body_text)


async def deliver_outbound(message: EmailMessage, recipient: str, mailbox_id: str | None = None) -> None:
    async with AsyncSessionLocal() as db:
        if mailbox_id:
            unsub = await db.execute(
                text(
                    """
                    SELECT 1
                    FROM unsubscribe_list
                    WHERE sender_mailbox_id = :mailbox_id AND recipient_email = :recipient
                    LIMIT 1
                    """
                ),
                {"mailbox_id": mailbox_id, "recipient": recipient.lower()},
            )
            if unsub.first() is not None:
                raise ValueError("Recipient unsubscribed")

        sender_key = None
        recipient_key = None
        if mailbox_id:
            sender_row = await db.execute(
                text(
                    """
                    SELECT private_key_encrypted
                    FROM pgp_keys
                    WHERE mailbox_id = :mailbox_id AND is_enabled = true
                    """
                ),
                {"mailbox_id": mailbox_id},
            )
            sender_key = sender_row.mappings().first()

        recipient_row = await db.execute(
            text(
                """
                SELECT k.public_key
                FROM pgp_keys k
                JOIN mailboxes m ON m.id = k.mailbox_id
                WHERE m.full_address = :recipient AND k.is_enabled = true
                """
            ),
            {"recipient": recipient.lower()},
        )
        recipient_key = recipient_row.mappings().first()

        body_text, body_html = _get_body(message)
        payload = body_html or body_text
        if payload and (sender_key or recipient_key):
            pgp_message = PGPMessage.new(payload)
            if sender_key:
                passphrase = message.get("X-PGP-Passphrase")
                if passphrase:
                    fernet = Fernet(settings.encryption_secret_key.encode("utf-8"))
                    private_key_armored = fernet.decrypt(
                        str(sender_key["private_key_encrypted"]).encode("utf-8")
                    ).decode("utf-8")
                    key, _ = PGPKey.from_blob(private_key_armored)
                    with key.unlock(passphrase):
                        signature = key.sign(pgp_message, hash=HashAlgorithm.SHA256)
                        pgp_message |= signature
                if "X-PGP-Passphrase" in message:
                    del message["X-PGP-Passphrase"]

            if recipient_key:
                public_key, _ = PGPKey.from_blob(recipient_key["public_key"])
                pgp_message = public_key.encrypt(pgp_message)

            _set_single_body(message, str(pgp_message))

        if mailbox_id and settings.tracking_enabled:
            if settings.tracking_base_url in body_html and "/px/" in body_html:
                message_id = message.get("Message-ID") or make_msgid()
                message["Message-ID"] = message_id
                await db.execute(
                    text(
                        """
                        INSERT INTO read_receipts (sender_mailbox_id, message_id, recipient_email, created_at)
                        VALUES (:sender_mailbox_id, :message_id, :recipient_email, now())
                        """
                    ),
                    {
                        "sender_mailbox_id": mailbox_id,
                        "message_id": message_id,
                        "recipient_email": recipient.lower(),
                    },
                )
                await db.commit()

        if mailbox_id:
            await fire_webhook(
                mailbox_id,
                "send",
                {
                    "to": recipient,
                    "subject": message.get("Subject", ""),
                    "message_id": message.get("Message-ID"),
                },
                db,
            )

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
