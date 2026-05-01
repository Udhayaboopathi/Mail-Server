from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TemplateCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    subject: str = Field(min_length=1, max_length=998)
    body_text: str | None = None
    body_html: str | None = None


class TemplateUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    subject: str | None = Field(default=None, min_length=1, max_length=998)
    body_text: str | None = None
    body_html: str | None = None


class TemplateResponse(BaseModel):
    id: str
    mailbox_id: str
    name: str
    subject: str
    body_text: str | None = None
    body_html: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
