from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_user_mailbox
from schemas.pgp import PgpGenerateRequest, PgpKeyResponse, PgpPublicKeyResponse
from services.pgp_service import generate_pgp_keypair, get_public_key

router = APIRouter(tags=["pgp"])


@router.post("/generate", response_model=PgpKeyResponse)
async def generate_keypair(payload: PgpGenerateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> PgpKeyResponse:
    data = await generate_pgp_keypair(str(mailbox.id), payload.passphrase, db)
    await db.execute(
        text("UPDATE pgp_keys SET is_enabled = true WHERE mailbox_id = :mailbox_id"),
        {"mailbox_id": str(mailbox.id)},
    )
    await db.commit()
    return PgpKeyResponse(fingerprint=data["fingerprint"], public_key=data["public_key_armored"])


@router.get("/public-key", response_model=PgpPublicKeyResponse)
async def public_key(mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> PgpPublicKeyResponse:
    key = await get_public_key(str(mailbox.id), db)
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PGP key not found")
    return PgpPublicKeyResponse(public_key=key)


@router.get("/public-key/{email}", response_model=PgpPublicKeyResponse)
async def lookup_public_key(email: str, db: AsyncSession = Depends(get_db)) -> PgpPublicKeyResponse:
    result = await db.execute(
        text(
            """
            SELECT k.public_key
            FROM pgp_keys k
            JOIN mailboxes m ON m.id = k.mailbox_id
            WHERE m.full_address = :email AND k.is_enabled = true
            """
        ),
        {"email": email.lower()},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PGP key not found")
    return PgpPublicKeyResponse(public_key=row["public_key"])


@router.delete("/key")
async def delete_key(mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(text("DELETE FROM pgp_keys WHERE mailbox_id = :mailbox_id"), {"mailbox_id": str(mailbox.id)})
    await db.commit()
    return {"status": "deleted"}
