from pathlib import Path
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.mailbox import Mailbox
from services.auth_service import AuthService


class MailboxService:
    @staticmethod
    async def provision_maildir(mailbox: Mailbox) -> str:
        base = Path(settings.maildir_base)
        mailbox_dir = base / str(mailbox.id)
        for folder in ("cur", "new", "tmp"):
            (mailbox_dir / folder).mkdir(parents=True, exist_ok=True)
        return str(mailbox_dir)

    @staticmethod
    async def deprovision_maildir(path: str | None) -> None:
        if path:
            base = Path(path)
            if base.exists():
                for child in base.rglob("*"):
                    if child.is_file():
                        child.unlink(missing_ok=True)

    @staticmethod
    async def set_password(mailbox: Mailbox, password: str) -> None:
        mailbox.user.hashed_password = AuthService.hash_password(password)
