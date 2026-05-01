from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user
from models.session import Session
from models.user import User
from schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenPair
from schemas.common import ActionResponse
from services.auth_service import AuthService
from middleware.rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
@limiter.limit("5/minute")
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await AuthService.authenticate_user(db, str(payload.email), payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = AuthService.create_access_token(user.email)
    refresh_token, refresh_hash = AuthService.create_refresh_token(user.email)
    await AuthService.store_refresh_token(db, user, refresh_hash, request.client.host if request.client else None)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    token_hash = AuthService.hash_token(payload.refresh_token)
    result = await db.execute(select(Session).where(Session.refresh_token_hash == token_hash))
    session_row = result.scalar_one_or_none()
    if session_row is None or session_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    result = await db.execute(select(User).where(User.id == session_row.user_id))
    user = result.scalar_one()
    access_token = AuthService.create_access_token(user.email)
    return TokenPair(access_token=access_token, refresh_token=payload.refresh_token)


@router.post("/logout", response_model=ActionResponse)
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db)) -> ActionResponse:
    await AuthService.invalidate_refresh_token(db, AuthService.hash_token(payload.refresh_token))
    return ActionResponse(status="ok")
