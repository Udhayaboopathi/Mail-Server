from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SharedMailboxCreateRequest(BaseModel):
    local_part: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=100)


class SharedMailboxMemberRequest(BaseModel):
    user_id: str
    permission: str = "read_write"


class SharedMailboxResponse(BaseModel):
    id: str
    mailbox_id: str
    domain_id: str
    display_name: str
    created_at: datetime
