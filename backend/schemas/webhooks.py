from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WebhookCreateRequest(BaseModel):
    url: str
    secret: str
    events: list[str] = ["receive", "send", "bounce"]


class WebhookUpdateRequest(BaseModel):
    url: str | None = None
    secret: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None


class WebhookResponse(BaseModel):
    id: str
    mailbox_id: str
    url: str
    secret: str
    events: list[str]
    is_active: bool
    last_triggered_at: datetime | None
    failure_count: int
    created_at: datetime
