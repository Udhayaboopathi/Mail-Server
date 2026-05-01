from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CalendarEventCreate(BaseModel):
    uid: str
    title: str
    description: str | None = None
    location: str | None = None
    start_at: datetime
    end_at: datetime
    all_day: bool = False
    rrule: str | None = None
    attendees: list[dict] = []
    linked_email_uid: str | None = None


class CalendarEventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day: bool | None = None
    rrule: str | None = None
    attendees: list[dict] | None = None
    linked_email_uid: str | None = None


class CalendarEventResponse(BaseModel):
    id: str
    mailbox_id: str
    uid: str
    title: str
    description: str | None = None
    location: str | None = None
    start_at: datetime
    end_at: datetime
    all_day: bool
    rrule: str | None = None
    attendees: list[dict] = []
    linked_email_uid: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
