from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AttachmentInput(BaseModel):
    filename: str
    content_base64: str
    mime_type: str


class MailSendRequest(BaseModel):
    to: list[str] = Field(min_length=1)
    cc: list[str] = []
    bcc: list[str] = []
    subject: str
    body_text: str
    body_html: str | None = None
    attachments: list[AttachmentInput] = []


class MailSummary(BaseModel):
    id: str
    uid: int
    sender: str
    recipients: list[str]
    subject: str
    date: datetime | None = None
    flags: list[str]
    size: int
    has_attachments: bool
    preview: str | None = None


class MailMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    uid: int
    folder: str
    headers: dict[str, str]
    body_text: str | None = None
    body_html: str | None = None
    attachments: list[AttachmentInput] = []
    flags: list[str] = []
    date: datetime | None = None


class FolderListResponse(BaseModel):
    folders: list[str]


class SearchResponse(BaseModel):
    results: list[MailSummary]

class MailFlagsRequest(BaseModel):
    seen: bool | None = None
    flagged: bool | None = None
    answered: bool | None = None

class MailMoveRequest(BaseModel):
    folder: str
