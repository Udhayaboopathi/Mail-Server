from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from deps import get_current_user
from schemas.auth import TokenPair
from schemas.auth_extended import (
    LoginActivityItem,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    TotpDisableRequest,
    TotpCodeRequest,
    TotpSetupResponse,
    TotpVerifyResponse,
)
from services.auth_service import AuthService
from services.totp_service import disable_totp, enable_totp, generate_totp_secret, verify_totp
from smtp.outbound import deliver_outbound

router = APIRouter(tags=["auth-extended"])


@router.post("/password-reset/request")
async def request_password_reset(payload: PasswordResetRequest, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": str(payload.email)})
    row = result.mappings().first()
    if row:
        token = secrets.token_hex(64)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.execute(
            text(
                """
                INSERT INTO password_reset_tokens (user_id, token, expires_at, created_at)
                VALUES (:user_id, :token, :expires_at, now())
                """
            ),
            {"user_id": str(row["id"]), "token": token, "expires_at": expires_at},
        )
        await db.commit()

        message = EmailMessage()
        message["From"] = f"no-reply@{settings.smtp_hostname}"
        message["To"] = str(payload.email)
        message["Subject"] = "Password reset"
        message.set_content(f"Reset your password: {settings.invite_base_url}/reset/{token}")
        await deliver_outbound(message, str(payload.email))

    return {"status": "ok"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(payload: PasswordResetConfirmRequest, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text(
            """
            SELECT id, user_id, expires_at, used_at
            FROM password_reset_tokens
            WHERE token = :token
            LIMIT 1
            """
        ),
        {"token": payload.token},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    if row["used_at"] is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token already used")
    if row["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")

    await db.execute(
        text("UPDATE users SET hashed_password = :hash WHERE id = :user_id"),
        {"hash": AuthService.hash_password(payload.new_password), "user_id": str(row["user_id"])},
    )
    await db.execute(
        text("UPDATE password_reset_tokens SET used_at = now() WHERE id = :id"), {"id": str(row["id"])},
    )
    await db.commit()
    return {"status": "updated"}


@router.post("/totp/setup", response_model=TotpSetupResponse)
async def totp_setup(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TotpSetupResponse:
    data = await generate_totp_secret(str(user.id), db)
    return TotpSetupResponse(secret=data["secret"], qr_uri=data["qr_code_uri"], backup_codes=data["backup_codes"])


@router.post("/totp/enable")
async def totp_enable(payload: TotpCodeRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    if not await enable_totp(str(user.id), payload.code, db):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
    return {"enabled": True}


@router.post("/totp/verify", response_model=TotpVerifyResponse)
async def totp_verify(payload: TotpCodeRequest, request: Request, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TotpVerifyResponse:
    if not await verify_totp(str(user.id), payload.code, db):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
    access_token = AuthService.create_access_token(user.email)
    refresh_token, refresh_hash = AuthService.create_refresh_token(user.email)
    await AuthService.store_refresh_token(db, user, refresh_hash, request.client.host if request.client else None)
    return TotpVerifyResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/totp/disable")
async def totp_disable(payload: TotpDisableRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    if not await disable_totp(str(user.id), payload.password, db):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password")
    return {"disabled": True}


@router.get("/login-activity", response_model=list[LoginActivityItem])
async def login_activity(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[LoginActivityItem]:
    result = await db.execute(
        text(
            """
            SELECT id, ip_address, user_agent, device_type, location, success, failure_reason, created_at
            FROM login_activity
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 50
            """
        ),
        {"user_id": str(user.id)},
    )
    return [LoginActivityItem(**row) for row in result.mappings().all()]
