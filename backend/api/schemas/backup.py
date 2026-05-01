from datetime import datetime
from pydantic import BaseModel


class BackupJobRead(BaseModel):
    id: str
    type: str
    status: str
    mailbox_id: str | None = None
    file_path: str | None = None
    file_size_mb: float | None = None
    total_messages: int | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


class BackupTriggerResponse(BaseModel):
    job_id: str
    status: str


class RestoreResult(BaseModel):
    status: str
    restored_mailboxes: int
    restored_messages: int
