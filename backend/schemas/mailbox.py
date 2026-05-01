import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MailboxCreate(BaseModel):
    user_id: uuid.UUID
    domain_id: uuid.UUID
    local_part: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8)
    quota_mb: int = Field(default=1024, gt=0)


class MailboxUpdate(BaseModel):
    password: str | None = None
    quota_mb: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class MailboxRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    domain_id: uuid.UUID
    local_part: str
    full_address: str
    quota_mb: int
    used_mb: float
    maildir_path: str | None = None
    is_active: bool
    created_at: datetime | None = None
