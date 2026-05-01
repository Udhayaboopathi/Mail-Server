from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import require_admin
from config import settings
from schemas.whitelabel import WhitelabelResponse, WhitelabelUpdateRequest

router = APIRouter(tags=["whitelabel"])

security = HTTPBearer(auto_error=False)


async def _optional_mailbox(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict | None:
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        email = str(payload.get("sub"))
    except JWTError:
        return None
    result = await db.execute(
        text(
            """
            SELECT m.id, m.domain_id, m.user_id
            FROM mailboxes m
            JOIN users u ON u.id = m.user_id
            WHERE u.email = :email AND m.is_active = true
            LIMIT 1
            """
        ),
        {"email": email},
    )
    return result.mappings().first()


@router.get("")
async def get_whitelabel(
    domain: str | None = Query(default=None),
    mailbox: dict | None = Depends(_optional_mailbox),
    db: AsyncSession = Depends(get_db),
) -> WhitelabelResponse:
    if domain:
        result = await db.execute(
            text(
                """
                SELECT whitelabel_logo_url AS logo_url,
                       whitelabel_primary_color AS primary_color,
                       whitelabel_company_name AS company_name
                FROM domains
                WHERE name = :domain
                LIMIT 1
                """
            ),
            {"domain": domain},
        )
    else:
        if mailbox is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        result = await db.execute(
            text(
                """
                SELECT whitelabel_logo_url AS logo_url,
                       whitelabel_primary_color AS primary_color,
                       whitelabel_company_name AS company_name
                FROM domains
                WHERE id = :domain_id
                LIMIT 1
                """
            ),
            {"domain_id": str(mailbox["domain_id"])},
        )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    return WhitelabelResponse(**row)


@router.patch("")
async def update_whitelabel(
    payload: WhitelabelUpdateRequest,
    _: object = Depends(require_admin),
    mailbox=Depends(_optional_mailbox),
    db: AsyncSession = Depends(get_db),
) -> WhitelabelResponse:
    if mailbox is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    result = await db.execute(
        text(
            """
            UPDATE domains
            SET whitelabel_logo_url = COALESCE(:logo_url, whitelabel_logo_url),
                whitelabel_primary_color = COALESCE(:primary_color, whitelabel_primary_color),
                whitelabel_company_name = COALESCE(:company_name, whitelabel_company_name)
            WHERE id = :domain_id
            RETURNING whitelabel_logo_url AS logo_url,
                      whitelabel_primary_color AS primary_color,
                      whitelabel_company_name AS company_name
            """
        ),
        {
            "logo_url": payload.logo_url,
            "primary_color": payload.primary_color,
            "company_name": payload.company_name,
            "domain_id": str(mailbox["domain_id"]),
        },
    )
    row = result.mappings().first()
    await db.commit()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    return WhitelabelResponse(**row)
