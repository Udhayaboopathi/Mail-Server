from __future__ import annotations

import asyncio
import logging
import mailbox
from datetime import date
from email import message_from_bytes
from email.message import EmailMessage
from email.policy import default
from email.utils import getaddresses
from pathlib import Path
from typing import Any

import bleach
import redis.asyncio as redis
from aiosmtpd.smtp import AuthResult, LoginPassword
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import AsyncSessionLocal
from models.alias import Alias
from models.domain import Domain
from models.mailbox import Mailbox
from models.user import User
from smtp.outbound import deliver_outbound
from services.auth_service import AuthService
from tasks.delivery import queue_delivery

logger = logging.getLogger(__name__)


class SMTPHandler:
    def __init__(self) -> None:
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def _verify_credentials(self, email: str, password: str) -> tuple[bool, str | None]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == email, User.is_active.is_(True)))
            user = result.scalar_one_or_none()
            if user is None:
                return False, None
            if not AuthService.verify_password(password, user.hashed_password):
                return False, None
            return True, str(user.id)

    async def _record_failed_auth(self, client_ip: str | None, email: str | None) -> None:
        if client_ip is None:
            return
        key = f"smtp:auth-fail:{client_ip}"
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 3600)
        logger.warning("SMTP AUTH FAIL ip=%s email=%s count=%s", client_ip, email or "", count)

    async def _reset_failed_auth(self, client_ip: str | None) -> None:
        if client_ip:
            await self.redis.delete(f"smtp:auth-fail:{client_ip}")

    async def _message_quota_ok(self, user_id: str | None) -> bool:
        if not user_id:
            return True
        key = f"smtp:hourly-sends:{user_id}"
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 3600)
        return count <= 100

    async def _is_local_domain(self, session: AsyncSession, domain_name: str) -> bool:
        result = await session.execute(select(Domain).where(Domain.name == domain_name, Domain.is_active.is_(True)))
        return result.scalar_one_or_none() is not None

    async def _alias_destination(self, session: AsyncSession, address: str) -> str | None:
        result = await session.execute(select(Alias).where(Alias.source_address == address, Alias.is_active.is_(True)))
        alias = result.scalar_one_or_none()
        return alias.destination_address if alias else None

    async def _mailbox_for_address(self, session: AsyncSession, address: str) -> Mailbox | None:
        result = await session.execute(
            select(Mailbox).where(Mailbox.full_address == address, Mailbox.is_active.is_(True)).options()
        )
        return result.scalar_one_or_none()

    async def _catch_all_destination(self, session: AsyncSession, domain_name: str) -> str | None:
        row = await session.execute(
            text(
                """
                SELECT a.destination_address
                FROM aliases a
                JOIN domains d ON d.id = a.domain_id
                WHERE d.name = :domain_name
                  AND a.is_active = true
                  AND a.is_catch_all = true
                ORDER BY a.created_at ASC
                LIMIT 1
                """
            ),
            {"domain_name": domain_name},
        )
        item = row.mappings().first()
        return str(item["destination_address"]) if item else None

    async def _maybe_send_autoresponder(self, session: AsyncSession, mailbox_row: Mailbox, sender_address: str | None) -> None:
        if not sender_address:
            return
        sender = sender_address.lower().strip()
        if "@" not in sender:
            return

        response = await session.execute(
            text(
                """
                SELECT id, is_enabled, subject, body, start_date, end_date, reply_once_per_sender
                FROM autoresponders
                WHERE mailbox_id = :mailbox_id
                LIMIT 1
                """
            ),
            {"mailbox_id": str(mailbox_row.id)},
        )
        autoresponder = response.mappings().first()
        if not autoresponder or not autoresponder["is_enabled"]:
            return

        today = date.today()
        start_date = autoresponder["start_date"]
        end_date = autoresponder["end_date"]
        if start_date and today < start_date:
            return
        if end_date and today > end_date:
            return

        if autoresponder["reply_once_per_sender"]:
            sent = await session.execute(
                text(
                    """
                    SELECT 1
                    FROM autoresponder_sent
                    WHERE autoresponder_id = :autoresponder_id
                      AND sent_to = :sent_to
                    LIMIT 1
                    """
                ),
                {"autoresponder_id": str(autoresponder["id"]), "sent_to": sender},
            )
            if sent.first() is not None:
                return

        reply = EmailMessage()
        reply["From"] = mailbox_row.full_address
        reply["To"] = sender
        reply["Subject"] = str(autoresponder["subject"])
        reply.set_content(str(autoresponder["body"]))
        await deliver_outbound(reply, sender)

        await session.execute(
            text(
                """
                INSERT INTO autoresponder_sent (autoresponder_id, sent_to)
                VALUES (:autoresponder_id, :sent_to)
                """
            ),
            {"autoresponder_id": str(autoresponder["id"]), "sent_to": sender},
        )
        await session.commit()

    async def _upsert_contacts_for_outbound(self, session: AsyncSession, sender_address: str | None, parsed_message) -> None:
        if not sender_address:
            return
        sender = sender_address.lower().strip()
        sender_lookup = await session.execute(
            text(
                """
                SELECT m.user_id
                FROM mailboxes m
                WHERE m.full_address = :sender
                LIMIT 1
                """
            ),
            {"sender": sender},
        )
        sender_row = sender_lookup.mappings().first()
        if sender_row is None:
            return

        recipients = getaddresses(parsed_message.get_all("To", []) + parsed_message.get_all("Cc", []))
        for display_name, email_address in recipients:
            normalized = email_address.lower().strip()
            if not normalized or "@" not in normalized:
                continue
            await session.execute(
                text(
                    """
                    INSERT INTO contacts (user_id, email, name)
                    VALUES (:user_id, :email, :name)
                    ON CONFLICT (user_id, email) DO UPDATE
                    SET name = COALESCE(EXCLUDED.name, contacts.name)
                    """
                ),
                {
                    "user_id": str(sender_row["user_id"]),
                    "email": normalized,
                    "name": display_name.strip() or None,
                },
            )
        await session.commit()

    async def _spam_check(self, raw_message: bytes) -> tuple[bytes, dict[str, str]]:
        process = await asyncio.create_subprocess_exec(
            "spamc",
            "-d",
            settings.spamassassin_host,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate(raw_message)
        checked = stdout or raw_message
        spam_headers = {"X-Spam-Checked": "yes", "X-Spam-Status": "No"}
        return checked, spam_headers

    async def _virus_check(self, raw_message: bytes) -> bool:
        try:
            reader, writer = await asyncio.open_connection(settings.clamav_host, 3310)
            writer.write(b"zINSTREAM\0")
            await writer.drain()
            for offset in range(0, len(raw_message), 8192):
                chunk = raw_message[offset : offset + 8192]
                writer.write(len(chunk).to_bytes(4, "big") + chunk)
                await writer.drain()
            writer.write((0).to_bytes(4, "big"))
            await writer.drain()
            response = await reader.readline()
            writer.close()
            await writer.wait_closed()
            return b"FOUND" not in response
        except OSError:
            return True

    async def _store_mail(self, session: AsyncSession, mailbox_row: Mailbox, raw_message: bytes, headers: dict[str, str]) -> None:
        mailbox_path = Path(mailbox_row.maildir_path or Path(settings.maildir_base) / str(mailbox_row.id))
        maildir = mailbox.Maildir(str(mailbox_path), create=True)
        parsed = message_from_bytes(raw_message, policy=default)
        maildir_message = mailbox.MaildirMessage(parsed)
        for header, value in headers.items():
            maildir_message[header] = value
        maildir.add(maildir_message)
        maildir.flush()
        size_mb = len(raw_message) / (1024 * 1024)
        await session.execute(update(Mailbox).where(Mailbox.id == mailbox_row.id).values(used_mb=Mailbox.used_mb + size_mb, maildir_path=str(mailbox_path)))
        await session.commit()

    async def auth_PLAIN(self, server, session, envelope, mechanism, auth_data):
        return await self._authenticate(server, auth_data)

    async def auth_LOGIN(self, server, session, envelope, mechanism, auth_data):
        return await self._authenticate(server, auth_data)

    async def _authenticate(self, server, auth_data: LoginPassword | bytes | None):
        client_ip = None
        if hasattr(server, "session") and getattr(server.session, "peer", None):
            client_ip = server.session.peer[0]

        if isinstance(auth_data, LoginPassword):
            login = auth_data.login.decode() if isinstance(auth_data.login, bytes) else str(auth_data.login)
            password = auth_data.password.decode() if isinstance(auth_data.password, bytes) else str(auth_data.password)
        elif isinstance(auth_data, bytes):
            try:
                login, password = auth_data.decode().split("\x00")[-2:]
            except Exception:
                await self._record_failed_auth(client_ip, None)
                return AuthResult(success=False)
        else:
            await self._record_failed_auth(client_ip, None)
            return AuthResult(success=False)

        ok, user_id = await self._verify_credentials(login, password)
        if not ok:
            await self._record_failed_auth(client_ip, login)
            return AuthResult(success=False)

        await self._reset_failed_auth(client_ip)
        return AuthResult(success=True)

    async def handle_MAIL(self, server, session, envelope, address, mail_options):
        envelope.mail_from = address
        return "250 OK"

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        async with AsyncSessionLocal() as db:
            recipient = address.lower()
            domain = recipient.split("@", 1)[1] if "@" in recipient else ""
            if not await self._is_local_domain(db, domain):
                mapped = await self._alias_destination(db, recipient)
                if mapped is None:
                    envelope.rcpt_tos.append(recipient)
                    return "250 OK"
                envelope.rcpt_tos.append(mapped)
                return "250 OK"
            mailbox_row = await self._mailbox_for_address(db, recipient)
            if mailbox_row is None:
                catch_all_target = await self._catch_all_destination(db, domain)
                if catch_all_target:
                    envelope.rcpt_tos.append(catch_all_target)
                    return "250 OK"
            envelope.rcpt_tos.append(recipient)
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        raw_message = envelope.content if isinstance(envelope.content, bytes) else envelope.content.encode("utf-8")
        if len(raw_message) > settings.max_message_size_mb * 1024 * 1024:
            return "552 5.3.4 Message too large"

        if not await self._virus_check(raw_message):
            return "550 5.7.1 Message rejected by antivirus"

        checked_message, spam_headers = await self._spam_check(raw_message)
        accepted_message = checked_message if checked_message else raw_message
        parsed = message_from_bytes(accepted_message, policy=default)

        async with AsyncSessionLocal() as db:
            for recipient in envelope.rcpt_tos:
                mailbox_row = await self._mailbox_for_address(db, recipient)
                if mailbox_row is not None:
                    await self._store_mail(db, mailbox_row, accepted_message, spam_headers)
                    await self._maybe_send_autoresponder(db, mailbox_row, envelope.mail_from)
                else:
                    message = EmailMessage()
                    message["From"] = envelope.mail_from
                    message["To"] = recipient
                    message["Subject"] = parsed.get("Subject", "")
                    message.set_content(str(parsed.get_body(preferencelist=("plain",)) or parsed.get_payload()))
                    queue_delivery.delay({"from": envelope.mail_from, "to": recipient, "subject": message["Subject"], "body_text": message.get_content()})
                    await deliver_outbound(message, recipient)
            await self._upsert_contacts_for_outbound(db, envelope.mail_from, parsed)
        return "250 2.0.0 Message accepted for delivery"
