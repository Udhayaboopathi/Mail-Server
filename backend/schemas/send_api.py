from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.mail import AttachmentInput


class SendApiRequest(BaseModel):
    from_name: str | None = None
    to: list[str] = Field(min_length=1)
    cc: list[str] | None = None
    bcc: list[str] | None = None
    subject: str
    text: str | None = None
    html: str | None = None
    attachments: list[AttachmentInput] | None = None
    track_opens: bool = False
    track_clicks: bool = False


class SendApiResponse(BaseModel):
    message_id: str
    queued: bool
