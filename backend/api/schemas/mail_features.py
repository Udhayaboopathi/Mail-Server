from datetime import date, datetime

from pydantic import BaseModel, Field

from schemas.mail import MailSendRequest


class MailScheduleRequest(MailSendRequest):
    send_at: datetime


class ScheduledEmailRead(BaseModel):
    id: str
    send_at: datetime
    to_addresses: list[str]
    subject: str
    status: str
    created_at: datetime | None = None


class UndoResponse(BaseModel):
    cancelled: bool
    message: str


class AutoresponderRequest(BaseModel):
    is_enabled: bool
    subject: str = Field(default="Out of Office", max_length=255)
    body: str
    start_date: date | None = None
    end_date: date | None = None
    reply_once_per_sender: bool = True


class AliasCreateRequest(BaseModel):
    local_part: str
    destination: str | None = None


class AliasRead(BaseModel):
    id: str
    source_address: str
    destination_address: str
    is_active: bool
    is_catch_all: bool
    forward_only: bool
    created_at: datetime | None = None
