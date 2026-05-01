from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from email.message import Message
from email.parser import BytesParser
from email.policy import default
from typing import Any

from passlib.context import CryptContext
from sqlalchemy import select

from database import AsyncSessionLocal
from models.mailbox import Mailbox
from models.user import User
from imap.maildir import MaildirBackend

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class IMAPSession:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    backend: MaildirBackend = field(default_factory=MaildirBackend)
    authenticated: bool = False
    user_email: str | None = None
    mailbox_id: str | None = None
    selected_folder: str = "Inbox"
    idle_mode: bool = False
    current_tag: str = "*"

    async def send(self, line: str) -> None:
        self.writer.write((line + "\r\n").encode("utf-8"))
        await self.writer.drain()

    async def greet(self) -> None:
        await self.send("* OK IMAP4rev1 Service Ready")

    async def run(self) -> None:
        await self.greet()
        while not self.reader.at_eof():
            raw = await self.reader.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="ignore").rstrip("\r\n")
            if self.idle_mode and line.upper() == "DONE":
                self.idle_mode = False
                await self.send(f"{self.current_tag} OK IDLE completed")
                continue
            if not line:
                continue
            await self.handle_command(line)
        self.writer.close()
        await self.writer.wait_closed()

    async def handle_command(self, line: str) -> None:
        parts = line.split(" ", 2)
        if len(parts) < 2:
            await self.send(f"{parts[0] if parts else '*'} BAD invalid command")
            return
        tag, command = parts[0], parts[1].upper()
        args = parts[2] if len(parts) > 2 else ""
        self.current_tag = tag
        handlers = {
            "CAPABILITY": self.capability,
            "NOOP": self.noop,
            "LOGOUT": self.logout,
            "LOGIN": self.login,
            "LIST": self.list_folders,
            "LSUB": self.list_folders,
            "SELECT": self.select,
            "EXAMINE": self.select,
            "CREATE": self.create_folder,
            "DELETE": self.delete_folder,
            "RENAME": self.rename_folder,
            "SUBSCRIBE": self.subscribe,
            "UNSUBSCRIBE": self.unsubscribe,
            "FETCH": self.fetch,
            "STORE": self.store,
            "SEARCH": self.search,
            "EXPUNGE": self.expunge,
            "COPY": self.copy,
            "MOVE": self.move,
            "APPEND": self.append,
            "IDLE": self.idle,
        }
        handler = handlers.get(command)
        if handler is None:
            await self.send(f"{tag} BAD unsupported command")
            return
        await handler(tag, args)

    async def capability(self, tag: str, args: str) -> None:
        await self.send("* CAPABILITY IMAP4rev1 IDLE MOVE UIDPLUS")
        await self.send(f"{tag} OK CAPABILITY completed")

    async def noop(self, tag: str, args: str) -> None:
        await self.send(f"{tag} OK NOOP completed")

    async def logout(self, tag: str, args: str) -> None:
        await self.send("* BYE IMAP server logging out")
        await self.send(f"{tag} OK LOGOUT completed")

    async def login(self, tag: str, args: str) -> None:
        try:
            email_address, password = self._parse_login(args)
        except ValueError:
            await self.send(f"{tag} BAD LOGIN requires username and password")
            return
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == email_address, User.is_active.is_(True)))
            user = result.scalar_one_or_none()
            if user is None or not pwd_context.verify(password, user.hashed_password):
                await self.send(f"{tag} NO LOGIN failed")
                return
            mailbox_result = await session.execute(select(Mailbox).where(Mailbox.user_id == user.id, Mailbox.is_active.is_(True)))
            mailbox = mailbox_result.scalar_one_or_none()
            if mailbox is None:
                await self.send(f"{tag} NO mailbox not found")
                return
            self.authenticated = True
            self.user_email = user.email
            self.mailbox_id = str(mailbox.id)
            await self.send(f"{tag} OK LOGIN completed")

    def _parse_login(self, args: str) -> tuple[str, str]:
        parts = args.split()
        if len(parts) < 2:
            raise ValueError("missing arguments")
        return parts[0].strip('"'), parts[1].strip('"')

    async def _require_auth(self, tag: str) -> bool:
        if not self.authenticated or self.mailbox_id is None:
            await self.send(f"{tag} NO Authenticate first")
            return False
        return True

    async def list_folders(self, tag: str, args: str) -> None:
        if not await self._require_auth(tag):
            return
        folders = self.backend.list_folders(self.mailbox_id or "")
        for folder in folders:
            await self.send(f'* LIST (\\HasNoChildren) "/" "{folder}"')
        await self.send(f"{tag} OK LIST completed")

    async def select(self, tag: str, args: str) -> None:
        if not await self._require_auth(tag):
            return
        folder = args.strip('"') or "Inbox"
        self.selected_folder = folder
        messages = self.backend.list_messages(self.mailbox_id or "", folder)
        await self.send(f"* {len(messages)} EXISTS")
        await self.send(f"* OK [UIDVALIDITY 1] UIDVALIDITY")
        await self.send(f"{tag} OK [READ-WRITE] SELECT completed")

    async def create_folder(self, tag: str, args: str) -> None:
        if not await self._require_auth(tag):
            return
        self.backend.ensure_folder(self.mailbox_id or "", args.strip('"'))
        await self.send(f"{tag} OK CREATE completed")

    async def delete_folder(self, tag: str, args: str) -> None:
        await self.send(f"{tag} OK DELETE completed")

    async def rename_folder(self, tag: str, args: str) -> None:
        await self.send(f"{tag} OK RENAME completed")

    async def subscribe(self, tag: str, args: str) -> None:
        await self.send(f"{tag} OK SUBSCRIBE completed")

    async def unsubscribe(self, tag: str, args: str) -> None:
        await self.send(f"{tag} OK UNSUBSCRIBE completed")

    async def fetch(self, tag: str, args: str) -> None:
        if not await self._require_auth(tag):
            return
        token = args.split()[0] if args else ""
        if not token.isdigit():
            await self.send(f"{tag} BAD FETCH requires uid")
            return
        uid = int(token)
        message = self.backend.read_message(self.mailbox_id or "", self.selected_folder, uid)
        if message is None:
            await self.send(f"{tag} NO message not found")
            return
        raw = message.as_bytes(policy=default)
        await self.send(f'* {uid} FETCH (UID {uid} FLAGS ({" ".join(message.get_flags())}) RFC822 {{{len(raw)}}}')
        await self.send(raw.decode("utf-8", errors="ignore"))
        await self.send(")")
        await self.send(f"{tag} OK FETCH completed")

    async def store(self, tag: str, args: str) -> None:
        if not await self._require_auth(tag):
            return
        parts = args.split(None, 2)
        if len(parts) < 3 or not parts[0].isdigit():
            await self.send(f"{tag} BAD STORE requires uid, flags")
            return
        uid = int(parts[0])
        flags = parts[2].strip().strip("()").replace("\\", "")
        self.backend.set_flags(self.mailbox_id or "", self.selected_folder, uid, flags)
        await self.send(f"{tag} OK STORE completed")

    async def search(self, tag: str, args: str) -> None:
        if not await self._require_auth(tag):
            return
        term = args.strip().lower()
        matches: list[int] = []
        for item in self.backend.list_messages(self.mailbox_id or "", self.selected_folder):
            haystack = " ".join([item["subject"], item["from"], item["to"], item["raw"].decode("utf-8", errors="ignore")]).lower()
            if not term or term == "all" or term in haystack:
                matches.append(int(item["uid"]))
        await self.send(f"* SEARCH {' '.join(str(uid) for uid in matches)}")
        await self.send(f"{tag} OK SEARCH completed")

    async def expunge(self, tag: str, args: str) -> None:
        await self.send(f"{tag} OK EXPUNGE completed")

    async def copy(self, tag: str, args: str) -> None:
        if not await self._require_auth(tag):
            return
        parts = args.split(None, 1)
        if len(parts) < 2 or not parts[0].isdigit():
            await self.send(f"{tag} BAD COPY requires uid and folder")
            return
        uid = int(parts[0])
        target = parts[1].strip('"')
        self.backend.copy(self.mailbox_id or "", self.selected_folder, target, uid)
        await self.send(f"{tag} OK COPY completed")

    async def move(self, tag: str, args: str) -> None:
        if not await self._require_auth(tag):
            return
        parts = args.split(None, 1)
        if len(parts) < 2 or not parts[0].isdigit():
            await self.send(f"{tag} BAD MOVE requires uid and folder")
            return
        uid = int(parts[0])
        target = parts[1].strip('"')
        self.backend.move(self.mailbox_id or "", self.selected_folder, target, uid)
        await self.send(f"{tag} OK MOVE completed")

    async def append(self, tag: str, args: str) -> None:
        if not await self._require_auth(tag):
            return
        folder = args.split(None, 1)[0].strip('"') if args else "Inbox"
        await self.send("+ Ready for literal data")
        data = await self.reader.readline()
        uid = self.backend.append(self.mailbox_id or "", folder, data)
        await self.send(f"{tag} OK [APPENDUID 1 {uid}] APPEND completed")

    async def idle(self, tag: str, args: str) -> None:
        self.idle_mode = True
        await self.send("+ idling")
