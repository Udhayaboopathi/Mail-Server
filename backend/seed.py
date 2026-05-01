import asyncio
from pathlib import Path

from sqlalchemy import select

from config import settings
from database import AsyncSessionLocal
from models.domain import Domain
from models.mailbox import Mailbox
from models.user import User
from services.auth_service import AuthService
from services.mailbox_service import MailboxService


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        admin_email = settings.super_admin_email
        admin_password = settings.super_admin_password
        result = await session.execute(select(User).where(User.email == admin_email))
        admin = result.scalar_one_or_none()
        if admin is None:
            admin = User(
                email=admin_email,
                hashed_password=AuthService.hash_password(admin_password),
                is_admin=True,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
        else:
            admin.hashed_password = AuthService.hash_password(admin_password)
            admin.is_admin = True
            admin.is_active = True
            await session.commit()
            await session.refresh(admin)

        result = await session.execute(select(Domain).where(Domain.name == settings.mail_domain))
        domain = result.scalar_one_or_none()
        if domain is None:
            domain = Domain(
                name=settings.mail_domain,
                is_active=True,
                spf_record=f"v=spf1 ip4:{settings.server_ip} mx ~all",
                dmarc_record=f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{settings.mail_domain}; pct=100",
            )
            session.add(domain)
            await session.commit()
            await session.refresh(domain)

        result = await session.execute(select(Mailbox).where(Mailbox.full_address == admin_email))
        mailbox = result.scalar_one_or_none()
        if mailbox is None:
            mailbox = Mailbox(
                user_id=admin.id,
                domain_id=domain.id,
                local_part="admin",
                full_address=admin_email,
                quota_mb=1024,
                used_mb=0,
                maildir_path=str(Path(settings.maildir_base) / str(admin.id)),
                is_active=True,
            )
            session.add(mailbox)
            await session.commit()
            await MailboxService.provision_maildir(mailbox)


if __name__ == "__main__":
    asyncio.run(seed())
