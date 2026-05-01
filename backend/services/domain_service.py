from base64 import b64encode
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.domain import Domain


class DomainService:
    @staticmethod
    async def dns_records(domain: Domain) -> dict[str, str]:
        public_key = "<pubkey>"
        if domain.dkim_private_key:
            private_value = domain.dkim_private_key
            private_path = Path(private_value)
            if private_path.exists():
                private_value = private_path.read_text(encoding="utf-8")
            private_key = serialization.load_pem_private_key(private_value.encode("utf-8"), password=None)
            public_key_bytes = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            public_key = b64encode(public_key_bytes).decode("ascii")
        return {
            "MX": f"10 {settings.mail_domain}.",
            "A": f"{settings.mail_domain}. -> YOUR_SERVER_IP",
            "SPF": "v=spf1 ip4:YOUR_SERVER_IP mx ~all",
            "DKIM": f"{domain.dkim_selector}._domainkey.{domain.name}. TXT v=DKIM1; k=rsa; p={public_key}",
            "DMARC": f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{domain.name}; pct=100",
        }

    @staticmethod
    async def get_domain_by_name(session: AsyncSession, name: str) -> Domain | None:
        result = await session.execute(select(Domain).where(Domain.name == name, Domain.is_active.is_(True)))
        return result.scalar_one_or_none()
