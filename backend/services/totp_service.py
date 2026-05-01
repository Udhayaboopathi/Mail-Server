from __future__ import annotations

import secrets

import pyotp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service import AuthService


_BACKUP_CODES_COUNT = 10


def _generate_backup_codes() -> list[str]:
    return [secrets.token_hex(4) for _ in range(_BACKUP_CODES_COUNT)]


async def generate_totp_secret(user_id: str, db: AsyncSession) -> dict:
    secret = pyotp.random_base32()
    backup_codes = _generate_backup_codes()
    email_result = await db.execute(text("SELECT email FROM users WHERE id = :user_id"), {"user_id": user_id})
    email_row = email_result.mappings().first()
    account_label = email_row["email"] if email_row else str(user_id)
    totp = pyotp.TOTP(secret)
    qr_uri = totp.provisioning_uri(name=account_label, issuer_name="Mail")

    await db.execute(
        text(
            """
            INSERT INTO totp_secrets (user_id, secret, is_enabled, backup_codes)
            VALUES (:user_id, :secret, false, :backup_codes)
            ON CONFLICT (user_id)
            DO UPDATE SET secret = EXCLUDED.secret, is_enabled = false, backup_codes = EXCLUDED.backup_codes
            """
        ),
        {"user_id": user_id, "secret": secret, "backup_codes": backup_codes},
    )
    await db.commit()
    return {"secret": secret, "qr_code_uri": qr_uri, "backup_codes": backup_codes}


async def enable_totp(user_id: str, code: str, db: AsyncSession) -> bool:
    result = await db.execute(
        text("SELECT secret FROM totp_secrets WHERE user_id = :user_id"), {"user_id": user_id}
    )
    row = result.mappings().first()
    if not row:
        return False
    totp = pyotp.TOTP(str(row["secret"]))
    if not totp.verify(code):
        return False
    await db.execute(text("UPDATE totp_secrets SET is_enabled = true WHERE user_id = :user_id"), {"user_id": user_id})
    await db.commit()
    return True


async def verify_totp(user_id: str, code: str, db: AsyncSession) -> bool:
    result = await db.execute(
        text("SELECT secret, is_enabled, backup_codes FROM totp_secrets WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    row = result.mappings().first()
    if not row or not row["is_enabled"]:
        return False

    backup_codes = list(row["backup_codes"] or [])
    if code in backup_codes:
        remaining = [item for item in backup_codes if item != code]
        await db.execute(
            text("UPDATE totp_secrets SET backup_codes = :backup_codes WHERE user_id = :user_id"),
            {"backup_codes": remaining, "user_id": user_id},
        )
        await db.commit()
        return True

    totp = pyotp.TOTP(str(row["secret"]))
    return bool(totp.verify(code, valid_window=1))


async def disable_totp(user_id: str, password: str, db: AsyncSession) -> bool:
    result = await db.execute(
        text("SELECT hashed_password FROM users WHERE id = :user_id"), {"user_id": user_id}
    )
    row = result.mappings().first()
    if row is None or not AuthService.verify_password(password, str(row["hashed_password"])):
        return False
    await db.execute(text("UPDATE totp_secrets SET is_enabled = false WHERE user_id = :user_id"), {"user_id": user_id})
    await db.commit()
    return True
