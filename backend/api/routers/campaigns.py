from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_user_mailbox
from schemas.campaigns import CampaignCreateRequest, CampaignListItem, CampaignRecipientList, CampaignUpdateRequest
from services.campaign_service import get_campaign_analytics
from tasks.campaign_tasks import send_campaign_task

router = APIRouter(tags=["campaigns"])


@router.get("", response_model=list[CampaignListItem])
async def list_campaigns(mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> list[CampaignListItem]:
    result = await db.execute(
        text("SELECT * FROM campaign_emails WHERE mailbox_id = :mailbox_id ORDER BY created_at DESC"),
        {"mailbox_id": str(mailbox.id)},
    )
    return [CampaignListItem(**row) for row in result.mappings().all()]


@router.post("", response_model=CampaignListItem)
async def create_campaign(payload: CampaignCreateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> CampaignListItem:
    result = await db.execute(
        text(
            """
            INSERT INTO campaign_emails (
                mailbox_id, name, subject, body_html, body_text, from_name, recipients,
                status, scheduled_at, created_at
            ) VALUES (
                :mailbox_id, :name, :subject, :body_html, :body_text, :from_name, CAST(:recipients AS jsonb),
                :status, :scheduled_at, now()
            )
            RETURNING *
            """
        ),
        {
            "mailbox_id": str(mailbox.id),
            "name": payload.name,
            "subject": payload.subject,
            "body_html": payload.body_html,
            "body_text": payload.body_text,
            "from_name": payload.from_name,
            "recipients": payload.recipients,
            "status": "scheduled" if payload.scheduled_at else "draft",
            "scheduled_at": payload.scheduled_at,
        },
    )
    row = result.mappings().first()
    await db.commit()
    return CampaignListItem(**row)


@router.patch("/{campaign_id}", response_model=CampaignListItem)
async def update_campaign(campaign_id: str, payload: CampaignUpdateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> CampaignListItem:
    result = await db.execute(
        text(
            """
            UPDATE campaign_emails
            SET name = COALESCE(:name, name),
                subject = COALESCE(:subject, subject),
                body_html = COALESCE(:body_html, body_html),
                body_text = COALESCE(:body_text, body_text),
                from_name = COALESCE(:from_name, from_name),
                recipients = COALESCE(CAST(:recipients AS jsonb), recipients),
                scheduled_at = COALESCE(:scheduled_at, scheduled_at)
            WHERE id = :id AND mailbox_id = :mailbox_id
            RETURNING *
            """
        ),
        {
            "id": campaign_id,
            "mailbox_id": str(mailbox.id),
            "name": payload.name,
            "subject": payload.subject,
            "body_html": payload.body_html,
            "body_text": payload.body_text,
            "from_name": payload.from_name,
            "recipients": payload.recipients,
            "scheduled_at": payload.scheduled_at,
        },
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    await db.commit()
    return CampaignListItem(**row)


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    status_row = await db.execute(
        text("SELECT status FROM campaign_emails WHERE id = :id AND mailbox_id = :mailbox_id"),
        {"id": campaign_id, "mailbox_id": str(mailbox.id)},
    )
    row = status_row.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if row["status"] != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft campaigns can be deleted")
    await db.execute(text("DELETE FROM campaign_emails WHERE id = :id"), {"id": campaign_id})
    await db.commit()
    return {"status": "deleted"}


@router.post("/{campaign_id}/send")
async def send_campaign(campaign_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    send_campaign_task.delay(campaign_id)
    return {"queued": True}


@router.post("/{campaign_id}/schedule")
async def schedule_campaign(campaign_id: str, payload: CampaignUpdateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    if payload.scheduled_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scheduled_at required")
    await db.execute(
        text("UPDATE campaign_emails SET scheduled_at = :scheduled_at, status = 'scheduled' WHERE id = :id"),
        {"scheduled_at": payload.scheduled_at, "id": campaign_id},
    )
    await db.commit()
    return {"scheduled": True}


@router.get("/{campaign_id}/analytics")
async def analytics(campaign_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    return await get_campaign_analytics(campaign_id, db)


@router.get("/{campaign_id}/recipients", response_model=CampaignRecipientList)
async def recipients(campaign_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> CampaignRecipientList:
    result = await db.execute(
        text("SELECT recipients FROM campaign_emails WHERE id = :id AND mailbox_id = :mailbox_id"),
        {"id": campaign_id, "mailbox_id": str(mailbox.id)},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    recipients = row["recipients"] or []
    return CampaignRecipientList(recipients=recipients)
