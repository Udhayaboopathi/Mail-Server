from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class DelegationGrantRequest(BaseModel):
    delegate_email: EmailStr
    permission: str = Field(default="send_on_behalf")


class DelegationRecord(BaseModel):
    id: str
    owner_mailbox_id: str
    delegate_user_id: str
    permission: str
    created_at: datetime
