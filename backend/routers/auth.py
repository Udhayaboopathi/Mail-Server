from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from deps import get_current_user
from models.session import Session
from models.user import User
from schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenPair
from schemas.common import ActionResponse
from services.auth_service import AuthService
from middleware.rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _device_type(user_agent: str | None) -> str:
    if not user_agent:
        return "unknown"
    lowered = user_agent.lower()
    if "tablet" in lowered or "ipad" in lowered:
        return "tablet"
    if "mobile" in lowered or "iphone" in lowered or "android" in lowered:
        return "mobile"
    return "desktop"


async def _lookup_location(ip: str | None) -> str | None:
    if not ip:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {}
            if settings.ip_geo_token:
                headers["Authorization"] = f"Bearer {settings.ip_geo_token}"
            response = await client.get(f"{settings.ip_geo_url}/{ip}", headers=headers)
            if response.status_code != 200:
                return None
            data = response.json()
            city = data.get("city")
            country = data.get("country")
            if city and country:
                return f"{city}, {country}"
            return country or city
    except Exception:
        return None


@router.post("/login", response_model=TokenPair)
@limiter.limit("5/minute")
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await AuthService.authenticate_user(db, str(payload.email), payload.password)
    if user is None:
        user_row = await db.execute(select(User).where(User.email == str(payload.email)))
        user_item = user_row.scalar_one_or_none()
        if user_item is not None:
            client_ip = request.client.host if request.client else "0.0.0.0"
            await db.execute(
                text(
                    """
                    INSERT INTO login_activity (user_id, ip_address, user_agent, device_type, location, success, failure_reason, created_at)
                    VALUES (:user_id, :ip_address, :user_agent, :device_type, :location, false, :failure_reason, now())
                    """
                ),
                {
                    "user_id": str(user_item.id),
                    "ip_address": client_ip,
                    "user_agent": request.headers.get("user-agent"),
                    "device_type": _device_type(request.headers.get("user-agent")),
                    "location": await _lookup_location(client_ip),
                    "failure_reason": "Invalid credentials",
                },
            )
            await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = AuthService.create_access_token(user.email)
    refresh_token, refresh_hash = AuthService.create_refresh_token(user.email)
    await AuthService.store_refresh_token(db, user, refresh_hash, request.client.host if request.client else None)
    client_ip = request.client.host if request.client else "0.0.0.0"
    await db.execute(
        text(
            """
            INSERT INTO login_activity (user_id, ip_address, user_agent, device_type, location, success, created_at)
            VALUES (:user_id, :ip_address, :user_agent, :device_type, :location, true, now())
            """
        ),
        {
            "user_id": str(user.id),
            "ip_address": client_ip,
            "user_agent": request.headers.get("user-agent"),
            "device_type": _device_type(request.headers.get("user-agent")),
            "location": await _lookup_location(client_ip),
        },
    )
    await db.commit()
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
