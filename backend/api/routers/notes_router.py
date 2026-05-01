from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_user_mailbox
from schemas.notes import NoteCreateRequest, NoteResponse, NoteUpdateRequest

router = APIRouter(tags=["notes"])


@router.get("", response_model=list[NoteResponse])
async def list_notes(mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> list[NoteResponse]:
    result = await db.execute(
        text("SELECT * FROM notes WHERE mailbox_id = :mailbox_id ORDER BY created_at DESC"),
        {"mailbox_id": str(mailbox.id)},
    )
    return [NoteResponse(**row) for row in result.mappings().all()]


@router.post("", response_model=NoteResponse)
async def create_note(payload: NoteCreateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> NoteResponse:
    result = await db.execute(
        text(
            """
            INSERT INTO notes (mailbox_id, title, body, linked_email_uid, created_at, updated_at)
            VALUES (:mailbox_id, :title, :body, :linked_email_uid, now(), now())
            RETURNING *
            """
        ),
        {
            "mailbox_id": str(mailbox.id),
            "title": payload.title,
            "body": payload.body,
            "linked_email_uid": payload.linked_email_uid,
        },
    )
    row = result.mappings().first()
    await db.commit()
    return NoteResponse(**row)


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(note_id: str, payload: NoteUpdateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> NoteResponse:
    result = await db.execute(
        text(
            """
            UPDATE notes
            SET title = COALESCE(:title, title),
                body = COALESCE(:body, body),
                linked_email_uid = COALESCE(:linked_email_uid, linked_email_uid),
                updated_at = now()
            WHERE id = :note_id AND mailbox_id = :mailbox_id
            RETURNING *
            """
        ),
        {
            "note_id": note_id,
            "mailbox_id": str(mailbox.id),
            "title": payload.title,
            "body": payload.body,
            "linked_email_uid": payload.linked_email_uid,
        },
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    await db.commit()
    return NoteResponse(**row)


@router.delete("/{note_id}")
async def delete_note(note_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text("DELETE FROM notes WHERE id = :note_id AND mailbox_id = :mailbox_id"),
        {"note_id": note_id, "mailbox_id": str(mailbox.id)},
    )
    await db.commit()
    return {"status": "deleted"}
