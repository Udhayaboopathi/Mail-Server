from __future__ import annotations

import secrets

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_user_mailbox
from schemas.api_keys import ApiKeyCreateRequest, ApiKeyCreatedResponse, ApiKeyResponse

router = APIRouter(tags=["api-keys"])


@router.get("", response_model=list[ApiKeyResponse])
async def list_keys(mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> list[ApiKeyResponse]:
    result = await db.execute(
        text(
            """
            SELECT id, name, key_prefix, scopes, rate_limit_per_hour, last_used_at, expires_at, is_active, created_at
            FROM api_keys
            WHERE mailbox_id = :mailbox_id
            ORDER BY created_at DESC
            """
        ),
        {"mailbox_id": str(mailbox.id)},
    )
    return [ApiKeyResponse(**row) for row in result.mappings().all()]


@router.post("", response_model=ApiKeyCreatedResponse)
async def create_key(payload: ApiKeyCreateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> ApiKeyCreatedResponse:
    raw_key = f"em_{secrets.token_urlsafe(32)}"
    key_hash = bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    prefix = raw_key[:8]

    result = await db.execute(
        text(
            """
            INSERT INTO api_keys (mailbox_id, domain_id, name, key_hash, key_prefix, scopes, rate_limit_per_hour, expires_at, created_at)
            VALUES (:mailbox_id, :domain_id, :name, :key_hash, :key_prefix, :scopes, :rate_limit, :expires_at, now())
            RETURNING id
            """
        ),
        {
            "mailbox_id": str(mailbox.id),
            "domain_id": str(mailbox.domain_id),
            "name": payload.name,
            "key_hash": key_hash,
            "key_prefix": prefix,
            "scopes": payload.scopes,
            "rate_limit": payload.rate_limit_per_hour,
            "expires_at": payload.expires_at,
        },
    )
    row = result.mappings().first()
    await db.commit()
    return ApiKeyCreatedResponse(id=str(row["id"]), key=raw_key, prefix=prefix)


@router.delete("/{key_id}")
async def delete_key(key_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text("DELETE FROM api_keys WHERE id = :key_id AND mailbox_id = :mailbox_id"),
        {"key_id": key_id, "mailbox_id": str(mailbox.id)},
    )
    await db.commit()
    return {"status": "deleted"}
