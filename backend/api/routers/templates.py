from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_user_mailbox
from schemas.templates import TemplateCreateRequest, TemplateResponse, TemplateUpdateRequest

router = APIRouter(tags=["templates"])


@router.get("", response_model=list[TemplateResponse])
async def list_templates(mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> list[TemplateResponse]:
    result = await db.execute(
        text("SELECT * FROM email_templates WHERE mailbox_id = :mailbox_id ORDER BY created_at DESC"),
        {"mailbox_id": str(mailbox.id)},
    )
    return [TemplateResponse(**row) for row in result.mappings().all()]


@router.post("", response_model=TemplateResponse)
async def create_template(payload: TemplateCreateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> TemplateResponse:
    result = await db.execute(
        text(
            """
            INSERT INTO email_templates (mailbox_id, name, subject, body_text, body_html, created_at, updated_at)
            VALUES (:mailbox_id, :name, :subject, :body_text, :body_html, now(), now())
            RETURNING *
            """
        ),
        {
            "mailbox_id": str(mailbox.id),
            "name": payload.name,
            "subject": payload.subject,
            "body_text": payload.body_text,
            "body_html": payload.body_html,
        },
    )
    row = result.mappings().first()
    await db.commit()
    return TemplateResponse(**row)


@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(template_id: str, payload: TemplateUpdateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> TemplateResponse:
    result = await db.execute(
        text(
            """
            UPDATE email_templates
            SET name = COALESCE(:name, name),
                subject = COALESCE(:subject, subject),
                body_text = COALESCE(:body_text, body_text),
                body_html = COALESCE(:body_html, body_html),
                updated_at = now()
            WHERE id = :template_id AND mailbox_id = :mailbox_id
            RETURNING *
            """
        ),
        {
            "template_id": template_id,
            "mailbox_id": str(mailbox.id),
            "name": payload.name,
            "subject": payload.subject,
            "body_text": payload.body_text,
            "body_html": payload.body_html,
        },
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    await db.commit()
    return TemplateResponse(**row)


@router.delete("/{template_id}")
async def delete_template(template_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text("DELETE FROM email_templates WHERE id = :template_id AND mailbox_id = :mailbox_id"),
        {"template_id": template_id, "mailbox_id": str(mailbox.id)},
    )
    await db.commit()
    return {"status": "deleted"}


@router.get("/{template_id}/use", response_model=TemplateResponse)
async def use_template(template_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> TemplateResponse:
    result = await db.execute(
        text("SELECT * FROM email_templates WHERE id = :template_id AND mailbox_id = :mailbox_id"),
        {"template_id": template_id, "mailbox_id": str(mailbox.id)},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return TemplateResponse(**row)
