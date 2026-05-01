import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AliasRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_address: str
    destination_address: str
    domain_id: uuid.UUID
    is_active: bool
    created_at: datetime | None = None

class AliasCreateRequest(BaseModel):
    source_address: str
    destination_address: str
    domain_id: str

class AliasUpdateRequest(BaseModel):
    destination_address: str | None = None
    is_active: bool | None = None
