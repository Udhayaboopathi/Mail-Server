from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import require_admin
from models.domain import Domain
from schemas.common import ActionResponse
from schemas.domain import DNSRecordsResponse, DomainCreate, DomainRead
from services.domain_service import DomainService

router = APIRouter(prefix="/api/domains", tags=["domains"])


@router.get("", response_model=list[DomainRead])
async def list_domains(_: Domain = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> list[Domain]:
    result = await db.execute(select(Domain).order_by(Domain.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=DomainRead)
async def create_domain(payload: DomainCreate, _: Domain = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> Domain:
    domain = Domain(name=payload.name)
    db.add(domain)
    await db.commit()
    await db.refresh(domain)
    return domain


@router.delete("/{domain_id}", response_model=ActionResponse)
async def delete_domain(domain_id: str, _: Domain = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> ActionResponse:
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    await db.delete(domain)
    await db.commit()
    return ActionResponse(status="deleted")


@router.get("/{domain_id}/dns-records", response_model=DNSRecordsResponse)
async def dns_records(domain_id: str, _: Domain = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> DNSRecordsResponse:
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    return DNSRecordsResponse(**await DomainService.dns_records(domain))
