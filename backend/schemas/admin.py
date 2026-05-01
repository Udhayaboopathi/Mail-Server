from pydantic import BaseModel, ConfigDict

from schemas.audit import AuditLogRead


class AdminStatsResponse(BaseModel):
    total_users: int
    total_domains: int
    total_mailboxes: int
    audit_logs: int
    mail_volume_today: int
    storage_used_mb: float


class AdminLogsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[AuditLogRead]
    page: int
    limit: int
