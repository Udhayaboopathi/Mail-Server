from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    due_at: datetime | None = None
    priority: str = Field(default="normal")
    linked_email_uid: str | None = None


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    due_at: datetime | None = None
    priority: str | None = None
    linked_email_uid: str | None = None


class TaskResponse(BaseModel):
    id: str
    mailbox_id: str
    title: str
    description: str | None
    due_at: datetime | None
    is_completed: bool
    completed_at: datetime | None
    priority: str
    linked_email_uid: str | None
    created_at: datetime
    updated_at: datetime | None
