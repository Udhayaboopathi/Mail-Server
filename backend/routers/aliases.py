from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import require_admin
from models.alias import Alias
from models.user import User
from schemas.common import ActionResponse
from schemas.alias import AliasCreateRequest, AliasRead, AliasUpdateRequest

router = APIRouter(prefix="/api/aliases", tags=["aliases"])


@router.get("", response_model=list[AliasRead])
async def list_aliases(_: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> list[Alias]:
    result = await db.execute(select(Alias).order_by(Alias.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=AliasRead)
async def create_alias(payload: AliasCreateRequest, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> Alias:
    alias = Alias(source_address=payload.source_address, destination_address=payload.destination_address, domain_id=payload.domain_id, is_active=True)
    db.add(alias)
    await db.commit()
    await db.refresh(alias)
    return alias


@router.patch("/{alias_id}", response_model=AliasRead)
async def update_alias(alias_id: str, payload: AliasUpdateRequest, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> Alias:
    result = await db.execute(select(Alias).where(Alias.id == alias_id))
    alias = result.scalar_one_or_none()
    if alias is None:
        raise HTTPException(status_code=404, detail="Alias not found")
    if payload.destination_address is not None:
        alias.destination_address = payload.destination_address
    if payload.is_active is not None:
        alias.is_active = payload.is_active
    await db.commit()
    await db.refresh(alias)
    return alias


@router.delete("/{alias_id}", response_model=ActionResponse)
async def delete_alias(alias_id: str, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> ActionResponse:
    result = await db.execute(select(Alias).where(Alias.id == alias_id))
    alias = result.scalar_one_or_none()
    if alias is None:
        raise HTTPException(status_code=404, detail="Alias not found")
    await db.delete(alias)
    await db.commit()
    return ActionResponse(status="deleted")
