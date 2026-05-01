from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CampaignRecipient(BaseModel):
    email: str
    name: str | None = None
    vars: dict | None = None


class CampaignCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    subject: str = Field(min_length=1, max_length=998)
    body_html: str
    body_text: str | None = None
    from_name: str | None = None
    recipients: list[CampaignRecipient]
    scheduled_at: datetime | None = None


class CampaignUpdateRequest(BaseModel):
    name: str | None = None
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    from_name: str | None = None
    recipients: list[CampaignRecipient] | None = None
    scheduled_at: datetime | None = None


class CampaignListItem(BaseModel):
    id: str
    mailbox_id: str
    name: str
    subject: str
    body_html: str
    body_text: str | None
    from_name: str | None
    recipients: list[CampaignRecipient]
    status: str
    scheduled_at: datetime | None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_recipients: int | None = None
    sent_count: int | None = None
    failed_count: int | None = None
    open_count: int | None = None
    click_count: int | None = None
    unsubscribe_count: int | None = None
    created_at: datetime


class CampaignRecipientList(BaseModel):
    recipients: list[CampaignRecipient]
