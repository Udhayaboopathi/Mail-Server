from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class NoteCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    body: str
    linked_email_uid: str | None = None


class NoteUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    body: str | None = None
    linked_email_uid: str | None = None


class NoteResponse(BaseModel):
    id: str
    mailbox_id: str
    title: str | None
    body: str
    linked_email_uid: str | None
    created_at: datetime
    updated_at: datetime | None
