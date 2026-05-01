from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user, get_user_mailbox
from models.user import User

router = APIRouter(tags=["contacts"])


class ContactCreate(BaseModel):
    email: str = Field(min_length=3, max_length=319)
    name: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class ContactUpdate(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=319)
    name: str | None = Field(default=None, max_length=255)
    notes: str | None = None


@router.get("")
async def search_contacts(
    q: str = Query(default=""),
    user: User = Depends(get_current_user),
    mailbox=Depends(get_user_mailbox),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    term = f"%{q.lower()}%"

    contacts_result = await db.execute(
        text(
            """
            SELECT id, email, name, notes, created_at
            FROM contacts
            WHERE user_id = :user_id
              AND (:query = '' OR LOWER(email) LIKE :term OR LOWER(COALESCE(name, '')) LIKE :term)
            ORDER BY created_at DESC
            LIMIT 50
            """
        ),
        {"user_id": str(user.id), "query": q, "term": term},
    )
    items = [dict(row) for row in contacts_result.mappings().all()]

    history_result = await db.execute(
        text(
            """
            SELECT DISTINCT addr AS email
            FROM (
                SELECT unnest(to_addresses) AS addr
                FROM scheduled_emails se
                JOIN mailboxes m ON m.id = se.mailbox_id
                WHERE m.user_id = :user_id
            ) t
            WHERE :query = '' OR LOWER(addr) LIKE :term
            LIMIT 25
            """
        ),
        {"user_id": str(user.id), "query": q, "term": term},
    )
    history = [dict(row) for row in history_result.mappings().all()]

    known = {item["email"].lower() for item in items}
    for row in history:
        email = str(row["email"]).lower()
        if email not in known:
            items.append({"id": None, "email": email, "name": None, "notes": None, "created_at": None})
            known.add(email)

    return items


@router.post("")
async def create_contact(payload: ContactCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text(
            """
            INSERT INTO contacts (user_id, email, name, notes)
            VALUES (:user_id, :email, :name, :notes)
            ON CONFLICT (user_id, email) DO UPDATE
            SET name = EXCLUDED.name,
                notes = EXCLUDED.notes
            RETURNING id, email, name, notes, created_at
            """
        ),
        {
            "user_id": str(user.id),
            "email": payload.email.lower().strip(),
            "name": payload.name,
            "notes": payload.notes,
        },
    )
    row = result.mappings().first()
    await db.commit()
    return dict(row)


@router.put("/{contact_id}")
async def update_contact(
    contact_id: str,
    payload: ContactUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    existing = await db.execute(
        text("SELECT id, email, name, notes, created_at FROM contacts WHERE id = :id AND user_id = :user_id"),
        {"id": contact_id, "user_id": str(user.id)},
    )
    row = existing.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    updated = await db.execute(
        text(
            """
            UPDATE contacts
            SET email = COALESCE(:email, email),
                name = COALESCE(:name, name),
                notes = :notes
            WHERE id = :id AND user_id = :user_id
            RETURNING id, email, name, notes, created_at
            """
        ),
        {
            "id": contact_id,
            "user_id": str(user.id),
            "email": payload.email.lower().strip() if payload.email else None,
            "name": payload.name,
            "notes": payload.notes,
        },
    )
    updated_row = updated.mappings().first()
    await db.commit()
    return dict(updated_row)


@router.delete("/{contact_id}")
async def delete_contact(contact_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text("DELETE FROM contacts WHERE id = :id AND user_id = :user_id RETURNING id"),
        {"id": contact_id, "user_id": str(user.id)},
    )
    row = result.mappings().first()
    await db.commit()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return {"status": "deleted"}
