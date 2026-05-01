from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ThreadLabel(BaseModel):
    name: str
    color: str


class ThreadSummary(BaseModel):
    thread_id: str
    subject: str
    participants: list[str]
    last_message_at: datetime | None
    message_count: int
    has_unread: bool
    latest_preview: str
    labels: list[ThreadLabel]
    last_sender: str | None = None


class ThreadMessage(BaseModel):
    uid: int | None
    folder: str
    from_: str | None = None
    to: str | None = None
    subject: str | None = None
    date: datetime | None = None
    flags: list[str] | None = None
    preview: str | None = None

    model_config = ConfigDict(populate_by_name=True, fields={"from_": "from"})
