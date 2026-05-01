import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    action: str
    target: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime | None = None
