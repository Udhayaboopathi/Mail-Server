from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_user_mailbox
from schemas.labels import LabelCreateRequest, LabelResponse, LabelUpdateRequest

router = APIRouter(tags=["labels"])


@router.get("", response_model=list[LabelResponse])
async def list_labels(mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> list[LabelResponse]:
    result = await db.execute(
        text("SELECT id, name, color, created_at FROM labels WHERE mailbox_id = :mailbox_id ORDER BY created_at DESC"),
        {"mailbox_id": str(mailbox.id)},
    )
    return [LabelResponse(**row) for row in result.mappings().all()]


@router.post("", response_model=LabelResponse)
async def create_label(payload: LabelCreateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> LabelResponse:
    result = await db.execute(
        text(
            """
            INSERT INTO labels (mailbox_id, name, color, created_at)
            VALUES (:mailbox_id, :name, :color, now())
            RETURNING id, name, color, created_at
            """
        ),
        {"mailbox_id": str(mailbox.id), "name": payload.name, "color": payload.color},
    )
    row = result.mappings().first()
    await db.commit()
    return LabelResponse(**row)


@router.patch("/{label_id}", response_model=LabelResponse)
async def update_label(label_id: str, payload: LabelUpdateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> LabelResponse:
    result = await db.execute(
        text(
            """
            UPDATE labels
            SET name = COALESCE(:name, name),
                color = COALESCE(:color, color)
            WHERE id = :label_id AND mailbox_id = :mailbox_id
            RETURNING id, name, color, created_at
            """
        ),
        {"label_id": label_id, "mailbox_id": str(mailbox.id), "name": payload.name, "color": payload.color},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found")
    await db.commit()
    return LabelResponse(**row)


@router.delete("/{label_id}")
async def delete_label(label_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(text("DELETE FROM labels WHERE id = :label_id AND mailbox_id = :mailbox_id"), {"label_id": label_id, "mailbox_id": str(mailbox.id)})
    await db.commit()
    return {"status": "deleted"}


@router.post("/{label_id}/apply/{email_uid}")
async def apply_label(label_id: str, email_uid: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text(
            """
            INSERT INTO email_labels (email_uid, label_id, mailbox_id)
            VALUES (:email_uid, :label_id, :mailbox_id)
            ON CONFLICT DO NOTHING
            """
        ),
        {"email_uid": email_uid, "label_id": label_id, "mailbox_id": str(mailbox.id)},
    )
    await db.commit()
    return {"status": "applied"}


@router.delete("/{label_id}/apply/{email_uid}")
async def remove_label(label_id: str, email_uid: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text(
            """
            DELETE FROM email_labels
            WHERE label_id = :label_id AND email_uid = :email_uid AND mailbox_id = :mailbox_id
            """
        ),
        {"label_id": label_id, "email_uid": email_uid, "mailbox_id": str(mailbox.id)},
    )
    await db.commit()
    return {"status": "removed"}
