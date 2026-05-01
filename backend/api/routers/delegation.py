from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user, get_user_mailbox
from imap.maildir import MaildirBackend
from schemas.delegation import DelegationGrantRequest, DelegationRecord

router = APIRouter(tags=["delegation"])

_backend = MaildirBackend()


@router.get("/granted", response_model=list[DelegationRecord])
async def granted(mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> list[DelegationRecord]:
    result = await db.execute(
        text(
            """
            SELECT d.id, d.owner_mailbox_id, d.delegate_user_id, d.permission, d.created_at
            FROM mailbox_delegations d
            WHERE d.owner_mailbox_id = :mailbox_id
            """
        ),
        {"mailbox_id": str(mailbox.id)},
    )
    return [DelegationRecord(**row) for row in result.mappings().all()]


@router.get("/received", response_model=list[DelegationRecord])
async def received(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[DelegationRecord]:
    result = await db.execute(
        text(
            """
            SELECT d.id, d.owner_mailbox_id, d.delegate_user_id, d.permission, d.created_at
            FROM mailbox_delegations d
            WHERE d.delegate_user_id = :user_id
            """
        ),
        {"user_id": str(user.id)},
    )
    return [DelegationRecord(**row) for row in result.mappings().all()]


@router.post("/grant")
async def grant(payload: DelegationGrantRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    user_result = await db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": payload.delegate_email})
    user_row = user_result.mappings().first()
    if user_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.execute(
        text(
            """
            INSERT INTO mailbox_delegations (owner_mailbox_id, delegate_user_id, permission, created_at)
            VALUES (:owner_mailbox_id, :delegate_user_id, :permission, now())
            ON CONFLICT (owner_mailbox_id, delegate_user_id) DO UPDATE SET permission = EXCLUDED.permission
            """
        ),
        {
            "owner_mailbox_id": str(mailbox.id),
            "delegate_user_id": str(user_row["id"]),
            "permission": payload.permission,
        },
    )
    await db.commit()
    return {"status": "granted"}


@router.delete("/revoke/{delegation_id}")
async def revoke(delegation_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text("DELETE FROM mailbox_delegations WHERE id = :id AND owner_mailbox_id = :mailbox_id"),
        {"id": delegation_id, "mailbox_id": str(mailbox.id)},
    )
    await db.commit()
    return {"status": "revoked"}


@router.get("/mailbox/{mailbox_id}/inbox")
async def delegated_inbox(mailbox_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT permission
            FROM mailbox_delegations
            WHERE owner_mailbox_id = :mailbox_id AND delegate_user_id = :user_id
            LIMIT 1
            """
        ),
        {"mailbox_id": mailbox_id, "user_id": str(user.id)},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access")
    return _backend.list_messages(mailbox_id, "Inbox")
