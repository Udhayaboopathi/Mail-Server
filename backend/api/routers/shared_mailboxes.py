from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user, get_user_mailbox, require_admin
from imap.maildir import MaildirBackend
from schemas.shared_mailboxes import SharedMailboxCreateRequest, SharedMailboxMemberRequest, SharedMailboxResponse

router = APIRouter(tags=["shared-mailboxes"])

_backend = MaildirBackend()


@router.get("", response_model=list[SharedMailboxResponse])
async def list_shared_mailboxes(_: object = Depends(require_admin), mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> list[SharedMailboxResponse]:
    result = await db.execute(
        text(
            """
            SELECT sm.id, sm.mailbox_id, sm.domain_id, sm.display_name, sm.created_at
            FROM shared_mailboxes sm
            WHERE sm.domain_id = :domain_id
            ORDER BY sm.created_at DESC
            """
        ),
        {"domain_id": str(mailbox.domain_id)},
    )
    return [SharedMailboxResponse(**row) for row in result.mappings().all()]


@router.post("", response_model=SharedMailboxResponse)
async def create_shared_mailbox(
    payload: SharedMailboxCreateRequest,
    _: object = Depends(require_admin),
    mailbox=Depends(get_user_mailbox),
    db: AsyncSession = Depends(get_db),
) -> SharedMailboxResponse:
    domain = await db.execute(text("SELECT name FROM domains WHERE id = :id"), {"id": str(mailbox.domain_id)})
    domain_row = domain.mappings().first()
    if domain_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

    local_part = payload.local_part.strip().lower()
    full_address = f"{local_part}@{domain_row['name']}"

    mailbox_row = await db.execute(
        text(
            """
            INSERT INTO mailboxes (user_id, domain_id, local_part, full_address, quota_mb, used_mb, is_active, created_at)
            VALUES (:user_id, :domain_id, :local_part, :full_address, 1024, 0, true, now())
            RETURNING id
            """
        ),
        {
            "user_id": str(mailbox.user_id),
            "domain_id": str(mailbox.domain_id),
            "local_part": local_part,
            "full_address": full_address,
        },
    )
    mailbox_id = mailbox_row.mappings().first()["id"]

    result = await db.execute(
        text(
            """
            INSERT INTO shared_mailboxes (mailbox_id, domain_id, display_name, created_at)
            VALUES (:mailbox_id, :domain_id, :display_name, now())
            RETURNING id, mailbox_id, domain_id, display_name, created_at
            """
        ),
        {"mailbox_id": str(mailbox_id), "domain_id": str(mailbox.domain_id), "display_name": payload.display_name},
    )
    row = result.mappings().first()
    await db.commit()
    return SharedMailboxResponse(**row)


@router.post("/{shared_mailbox_id}/members")
async def add_member(
    shared_mailbox_id: str,
    payload: SharedMailboxMemberRequest,
    _: object = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await db.execute(
        text(
            """
            INSERT INTO shared_mailbox_members (shared_mailbox_id, user_id, permission, added_at)
            VALUES (:shared_mailbox_id, :user_id, :permission, now())
            ON CONFLICT (shared_mailbox_id, user_id) DO UPDATE SET permission = EXCLUDED.permission
            """
        ),
        {
            "shared_mailbox_id": shared_mailbox_id,
            "user_id": payload.user_id,
            "permission": payload.permission,
        },
    )
    await db.commit()
    return {"status": "added"}


@router.delete("/{shared_mailbox_id}/members/{user_id}")
async def remove_member(
    shared_mailbox_id: str,
    user_id: str,
    _: object = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await db.execute(
        text(
            "DELETE FROM shared_mailbox_members WHERE shared_mailbox_id = :shared_mailbox_id AND user_id = :user_id"),
        {"shared_mailbox_id": shared_mailbox_id, "user_id": user_id},
    )
    await db.commit()
    return {"status": "removed"}


@router.get("/{shared_mailbox_id}/inbox")
async def get_shared_inbox(shared_mailbox_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    membership = await db.execute(
        text(
            """
            SELECT sm.mailbox_id
            FROM shared_mailbox_members smm
            JOIN shared_mailboxes sm ON sm.id = smm.shared_mailbox_id
            WHERE smm.shared_mailbox_id = :shared_mailbox_id AND smm.user_id = :user_id
            LIMIT 1
            """
        ),
        {"shared_mailbox_id": shared_mailbox_id, "user_id": str(user.id)},
    )
    row = membership.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")

    messages = _backend.list_messages(str(row["mailbox_id"]), "Inbox")
    return messages
