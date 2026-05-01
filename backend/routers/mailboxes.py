from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import require_admin
from models.domain import Domain
from models.mailbox import Mailbox
from models.user import User
from schemas.common import ActionResponse
from schemas.mailbox import MailboxCreate, MailboxRead, MailboxUpdate
from services.auth_service import AuthService
from services.mailbox_service import MailboxService

router = APIRouter(prefix="/api/mailboxes", tags=["mailboxes"])


@router.get("", response_model=list[MailboxRead])
async def list_mailboxes(_: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> list[Mailbox]:
    result = await db.execute(select(Mailbox).order_by(Mailbox.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=MailboxRead)
async def create_mailbox(payload: MailboxCreate, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> Mailbox:
    result = await db.execute(select(User).where(User.id == payload.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    domain_result = await db.execute(select(Domain).where(Domain.id == payload.domain_id))
    domain = domain_result.scalar_one_or_none()
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    mailbox = Mailbox(user_id=payload.user_id, domain_id=payload.domain_id, local_part=payload.local_part, full_address=f"{payload.local_part}@{domain.name}", quota_mb=payload.quota_mb)
    db.add(mailbox)
    await db.commit()
    await db.refresh(mailbox)
    mailbox.maildir_path = await MailboxService.provision_maildir(mailbox)
    user.hashed_password = AuthService.hash_password(payload.password)
    await db.commit()
    await db.refresh(mailbox)
    return mailbox


@router.patch("/{mailbox_id}", response_model=MailboxRead)
async def update_mailbox(mailbox_id: str, payload: MailboxUpdate, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> Mailbox:
    result = await db.execute(select(Mailbox).where(Mailbox.id == mailbox_id))
    mailbox = result.scalar_one_or_none()
    if mailbox is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mailbox not found")
    if payload.quota_mb is not None:
        mailbox.quota_mb = payload.quota_mb
    if payload.is_active is not None:
        mailbox.is_active = payload.is_active
    if payload.password is not None:
        mailbox.user.hashed_password = AuthService.hash_password(payload.password)
    await db.commit()
    await db.refresh(mailbox)
    return mailbox


@router.delete("/{mailbox_id}", response_model=ActionResponse)
async def delete_mailbox(mailbox_id: str, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> ActionResponse:
    result = await db.execute(select(Mailbox).where(Mailbox.id == mailbox_id))
    mailbox = result.scalar_one_or_none()
    if mailbox is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mailbox not found")
    await db.delete(mailbox)
    await db.commit()
    return ActionResponse(status="deleted")
