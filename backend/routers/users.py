from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import require_admin
from models.user import User
from schemas.common import ActionResponse
from schemas.user import UserCreate, UserRead, UserUpdate
from services.auth_service import AuthService

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserRead])
async def list_users(_: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=UserRead)
async def create_user(payload: UserCreate, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> User:
    user = User(email=str(payload.email), hashed_password=AuthService.hash_password(payload.password), is_admin=payload.is_admin, is_active=payload.is_active)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(user_id: str, payload: UserUpdate, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.email is not None:
        user.email = str(payload.email)
    if payload.password is not None:
        user.hashed_password = AuthService.hash_password(payload.password)
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.is_active is not None:
        user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=ActionResponse)
async def delete_user(user_id: str, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> ActionResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.delete(user)
    await db.commit()
    return ActionResponse(status="deleted")
