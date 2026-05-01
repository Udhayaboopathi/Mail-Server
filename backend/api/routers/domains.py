from __future__ import annotations

import base64
import hashlib
import re
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.domain import (
	DNSAutoConfigRequest,
	DNSAutoConfigResponse,
	DNSGuideResponse,
	DNSRecordsResponse,
	DNSVerifyResponse,
	DomainCreate,
	DomainCreateResponse,
	DomainRead,
	DomainUserCreate,
	DomainUserRead,
)
from config import settings
from database import get_db
from deps import require_admin
from models.domain import Domain
from models.mailbox import Mailbox
from models.user import User
from schemas.common import ActionResponse
from services import cloudflare_service
from services.auth_service import AuthService
from services.dns_guide_service import generate_dns_guide
from services.mailbox_service import MailboxService

router = APIRouter(prefix="/api/domains", tags=["domains"])


def _fernet() -> Fernet:
	digest = hashlib.sha256(settings.jwt_secret_key.encode("utf-8")).digest()
	key = base64.urlsafe_b64encode(digest)
	return Fernet(key)


def _encrypt_private_key(private_key_pem: str) -> str:
	token = _fernet().encrypt(private_key_pem.encode("utf-8")).decode("utf-8")
	return f"enc:{token}"


def _decrypt_private_key(stored_value: str | None) -> str:
	if not stored_value:
		raise ValueError("Missing DKIM private key")
	if stored_value.startswith("enc:"):
		token = stored_value.split(":", 1)[1]
		return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
	return stored_value


def _extract_dkim_public_key(stored_private_key: str | None) -> str:
	private_text = _decrypt_private_key(stored_private_key)
	private_key = serialization.load_pem_private_key(private_text.encode("utf-8"), password=None)
	public_key_bytes = private_key.public_key().public_bytes(
		encoding=serialization.Encoding.DER,
		format=serialization.PublicFormat.SubjectPublicKeyInfo,
	)
	return base64.b64encode(public_key_bytes).decode("ascii")


def _generate_dkim_keypair() -> tuple[str, str]:
	private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
	private_pem = private_key.private_bytes(
		encoding=serialization.Encoding.PEM,
		format=serialization.PrivateFormat.PKCS8,
		encryption_algorithm=serialization.NoEncryption(),
	).decode("utf-8")
	public_der = private_key.public_key().public_bytes(
		encoding=serialization.Encoding.DER,
		format=serialization.PublicFormat.SubjectPublicKeyInfo,
	)
	return private_pem, base64.b64encode(public_der).decode("ascii")


async def _get_dns_state(db: AsyncSession, domain_id: str) -> dict:
	row = await db.execute(
		text(
			"""
			SELECT cloudflare_zone_id, cloudflare_auto_dns, dns_verified, dns_verified_at
			FROM domains
			WHERE id = CAST(:domain_id AS UUID)
			"""
		),
		{"domain_id": domain_id},
	)
	state = row.mappings().first()
	return dict(state) if state else {}


async def _set_domain_dns_columns(db: AsyncSession, domain_id: str, **fields) -> None:
	if not fields:
		return
	set_parts = []
	params = {"domain_id": domain_id}
	for idx, (name, value) in enumerate(fields.items(), start=1):
		param_name = f"value_{idx}"
		set_parts.append(f"{name} = :{param_name}")
		params[param_name] = value
	await db.execute(
		text(f"UPDATE domains SET {', '.join(set_parts)} WHERE id = CAST(:domain_id AS UUID)"),
		params,
	)


@router.get("", response_model=list[DomainRead])
async def list_domains(_: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> list[DomainRead]:
	result = await db.execute(select(Domain).order_by(Domain.created_at.desc()))
	domains = list(result.scalars().all())
	output: list[DomainRead] = []
	for domain in domains:
		state = await _get_dns_state(db, str(domain.id))
		output.append(
			DomainRead(
				id=domain.id,
				name=domain.name,
				is_active=domain.is_active,
				dkim_selector=domain.dkim_selector,
				spf_record=domain.spf_record,
				dmarc_record=domain.dmarc_record,
				cloudflare_zone_id=state.get("cloudflare_zone_id"),
				dns_verified=bool(state.get("dns_verified", False)),
				created_at=domain.created_at,
			)
		)
	return output


@router.post("", response_model=DomainCreateResponse)
async def create_domain(
	payload: DomainCreate,
	_: User = Depends(require_admin),
	db: AsyncSession = Depends(get_db),
) -> DomainCreateResponse:
	existing = await db.execute(select(Domain).where(Domain.name == payload.name.lower().strip()))
	if existing.scalar_one_or_none() is not None:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Domain already exists")

	private_pem, public_key = _generate_dkim_keypair()
	domain = Domain(
		name=payload.name.lower().strip(),
		dkim_selector="mail",
		dkim_private_key=_encrypt_private_key(private_pem),
	)
	db.add(domain)
	await db.commit()
	await db.refresh(domain)

	await _set_domain_dns_columns(db, str(domain.id), dns_verified=False)
	await db.commit()

	return DomainCreateResponse(
		id=domain.id,
		name=domain.name,
		dkim_selector=domain.dkim_selector,
		dkim_public_key=public_key,
		dns_verified=False,
		created_at=domain.created_at,
	)


@router.delete("/{domain_id}", response_model=ActionResponse)
async def delete_domain(domain_id: str, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> ActionResponse:
	result = await db.execute(select(Domain).where(Domain.id == domain_id))
	domain = result.scalar_one_or_none()
	if domain is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
	await db.delete(domain)
	await db.commit()
	return ActionResponse(status="deleted")


@router.get("/{domain_id}/dns-records", response_model=DNSRecordsResponse)
async def dns_records(domain_id: str, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> DNSRecordsResponse:
	result = await db.execute(select(Domain).where(Domain.id == domain_id))
	domain = result.scalar_one_or_none()
	if domain is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

	public_key = _extract_dkim_public_key(domain.dkim_private_key)
	server_ip = settings.server_ip or "YOUR_SERVER_IP"
	return DNSRecordsResponse(
		MX=f"10 mail.{domain.name}.",
		A=f"mail.{domain.name}. -> {server_ip}",
		SPF=f"v=spf1 ip4:{server_ip} mx ~all",
		DKIM=f"{domain.dkim_selector}._domainkey.{domain.name}. TXT v=DKIM1; k=rsa; p={public_key}",
		DMARC=f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{domain.name}; pct=100",
	)


@router.post("/{domain_id}/dns/auto", response_model=DNSAutoConfigResponse)
async def configure_dns_auto(
	domain_id: str,
	payload: DNSAutoConfigRequest,
	_: User = Depends(require_admin),
	db: AsyncSession = Depends(get_db),
) -> DNSAutoConfigResponse:
	if not settings.server_ip:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SERVER_IP is not configured")

	result = await db.execute(select(Domain).where(Domain.id == domain_id))
	domain = result.scalar_one_or_none()
	if domain is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

	if payload.cloudflare_zone_id:
		await _set_domain_dns_columns(db, domain_id, cloudflare_zone_id=payload.cloudflare_zone_id)
		await db.commit()

	dkim_public_key = _extract_dkim_public_key(domain.dkim_private_key)
	try:
		records_created = await cloudflare_service.configure_domain_dns(
			domain_name=domain.name,
			server_ip=settings.server_ip,
			dkim_public_key=dkim_public_key,
			dkim_selector=domain.dkim_selector,
		)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
	except Exception as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

	await _set_domain_dns_columns(db, domain_id, cloudflare_auto_dns=True)
	await db.commit()

	return DNSAutoConfigResponse(
		success=True,
		records_created=records_created,
		message="DNS configured successfully via Cloudflare",
	)


@router.get("/{domain_id}/dns/guide", response_model=DNSGuideResponse)
async def dns_guide(domain_id: str, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> DNSGuideResponse:
	if not settings.server_ip:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SERVER_IP is not configured")

	result = await db.execute(select(Domain).where(Domain.id == domain_id))
	domain = result.scalar_one_or_none()
	if domain is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

	dkim_public_key = _extract_dkim_public_key(domain.dkim_private_key)
	guide = generate_dns_guide(
		domain_name=domain.name,
		server_ip=settings.server_ip,
		dkim_public_key=dkim_public_key,
		dkim_selector=domain.dkim_selector,
	)
	return DNSGuideResponse(**guide)


@router.post("/{domain_id}/dns/verify", response_model=DNSVerifyResponse)
async def verify_dns(domain_id: str, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> DNSVerifyResponse:
	if not settings.server_ip:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SERVER_IP is not configured")

	result = await db.execute(select(Domain).where(Domain.id == domain_id))
	domain = result.scalar_one_or_none()
	if domain is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

	verification = await cloudflare_service.verify_dns_records(domain.name, settings.server_ip)
	verified_at: datetime | None = None
	if verification["all_valid"]:
		verified_at = datetime.now(timezone.utc)
		await _set_domain_dns_columns(db, domain_id, dns_verified=True, dns_verified_at=verified_at)
		await db.commit()

	return DNSVerifyResponse(**verification, verified_at=verified_at)


@router.get("/{domain_id}/users", response_model=list[DomainUserRead])
async def list_domain_users(
	domain_id: str,
	_: User = Depends(require_admin),
	db: AsyncSession = Depends(get_db),
) -> list[DomainUserRead]:
	result = await db.execute(
		select(Mailbox).where(Mailbox.domain_id == domain_id).order_by(Mailbox.created_at.desc())
	)
	mailboxes = list(result.scalars().all())
	return [
		DomainUserRead(
			id=item.id,
			full_address=item.full_address,
			local_part=item.local_part,
			quota_mb=item.quota_mb,
			used_mb=item.used_mb,
			is_active=item.is_active,
			created_at=item.created_at,
		)
		for item in mailboxes
	]


@router.post("/{domain_id}/users", response_model=DomainUserRead)
async def create_domain_user(
	domain_id: str,
	payload: DomainUserCreate,
	_: User = Depends(require_admin),
	db: AsyncSession = Depends(get_db),
) -> DomainUserRead:
	result = await db.execute(select(Domain).where(Domain.id == domain_id))
	domain = result.scalar_one_or_none()
	if domain is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

	local_part = payload.local_part.strip().lower()
	if not re.fullmatch(r"[a-z0-9.-]{1,64}", local_part):
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail="local_part must be alphanumeric and may include dots and hyphens (max 64 chars)",
		)

	full_address = f"{local_part}@{domain.name}"
	mailbox_exists = await db.execute(select(Mailbox).where(Mailbox.full_address == full_address))
	if mailbox_exists.scalar_one_or_none() is not None:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mailbox already exists")

	user_exists = await db.execute(select(User).where(User.email == full_address))
	if user_exists.scalar_one_or_none() is not None:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

	user = User(email=full_address, hashed_password=AuthService.hash_password(payload.password), is_admin=False, is_active=True)
	db.add(user)
	await db.flush()

	mailbox = Mailbox(
		user_id=user.id,
		domain_id=domain.id,
		local_part=local_part,
		full_address=full_address,
		quota_mb=payload.quota_mb,
		used_mb=0.0,
		is_active=True,
	)
	db.add(mailbox)
	await db.flush()

	mailbox.maildir_path = await MailboxService.provision_maildir(mailbox)
	await db.commit()
	await db.refresh(mailbox)

	return DomainUserRead(
		id=mailbox.id,
		full_address=mailbox.full_address,
		local_part=mailbox.local_part,
		quota_mb=mailbox.quota_mb,
		used_mb=mailbox.used_mb,
		is_active=mailbox.is_active,
		created_at=mailbox.created_at,
	)
