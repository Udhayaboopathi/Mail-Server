from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import require_admin
from models.audit_log import AuditLog
from models.domain import Domain
from models.mailbox import Mailbox
from models.user import User
from schemas.admin import AdminLogsResponse, AdminStatsResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsResponse)
async def stats(_: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> AdminStatsResponse:
    users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    domains = (await db.execute(select(func.count()).select_from(Domain))).scalar_one()
    mailboxes = (await db.execute(select(func.count()).select_from(Mailbox))).scalar_one()
    logs = (await db.execute(select(func.count()).select_from(AuditLog))).scalar_one()
    return AdminStatsResponse(
        total_users=users,
        total_domains=domains,
        total_mailboxes=mailboxes,
        audit_logs=logs,
        mail_volume_today=0,
        storage_used_mb=0,
    )


@router.get("/logs", response_model=AdminLogsResponse)
async def logs(page: int = 1, limit: int = 50, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> AdminLogsResponse:
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset((page - 1) * limit))
    return AdminLogsResponse(items=list(result.scalars().all()), page=page, limit=limit)
