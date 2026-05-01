from __future__ import annotations

from typing import Any

import dns.resolver
import httpx

from config import settings

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareServiceError(Exception):
    pass


async def _request(method: str, path: str, *, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None) -> dict[str, Any]:
    if not settings.cloudflare_api_token:
        raise CloudflareServiceError("CLOUDFLARE_API_TOKEN is not configured")

    headers = {
        "Authorization": f"Bearer {settings.cloudflare_api_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(base_url=CLOUDFLARE_API_BASE, timeout=20.0) as client:
        response = await client.request(method, path, params=params, json=json, headers=headers)
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success", False):
            errors = payload.get("errors") or []
            raise CloudflareServiceError(f"Cloudflare API error: {errors}")
        return payload


async def get_zone_id(domain_name: str) -> str | None:
    payload = await _request("GET", "/zones", params={"name": domain_name, "status": "active"})
    zones = payload.get("result") or []
    if not zones:
        return None
    return zones[0].get("id")


async def create_dns_record(zone_id: str, record: dict[str, Any]) -> dict[str, Any]:
    payload = await _request("POST", f"/zones/{zone_id}/dns_records", json=record)
    return payload.get("result") or {}


async def delete_dns_record(zone_id: str, record_id: str) -> bool:
    payload = await _request("DELETE", f"/zones/{zone_id}/dns_records/{record_id}")
    return bool(payload.get("success"))


async def list_dns_records(zone_id: str, name: str) -> list[dict[str, Any]]:
    payload = await _request("GET", f"/zones/{zone_id}/dns_records", params={"name": name})
    return payload.get("result") or []


async def upsert_record(zone_id: str, record: dict[str, Any]) -> dict[str, Any]:
    existing = await list_dns_records(zone_id, record["name"])
    for item in existing:
        if item.get("type") == record.get("type"):
            record_id = item.get("id")
            if record_id:
                await delete_dns_record(zone_id, record_id)
    return await create_dns_record(zone_id, record)


async def configure_domain_dns(
    domain_name: str,
    server_ip: str,
    dkim_public_key: str,
    dkim_selector: str = "mail",
) -> dict[str, Any]:
    zone_id = await get_zone_id(domain_name)
    if zone_id is None:
        raise ValueError(f"Cloudflare zone not found for domain {domain_name}")

    records = {
        "mx": {
            "type": "MX",
            "name": domain_name,
            "content": f"mail.{domain_name}",
            "priority": 10,
            "ttl": 3600,
        },
        "a": {
            "type": "A",
            "name": f"mail.{domain_name}",
            "content": server_ip,
            "ttl": 3600,
        },
        "spf": {
            "type": "TXT",
            "name": domain_name,
            "content": f"v=spf1 ip4:{server_ip} mx ~all",
            "ttl": 3600,
        },
        "dkim": {
            "type": "TXT",
            "name": f"{dkim_selector}._domainkey.{domain_name}",
            "content": f"v=DKIM1; k=rsa; p={dkim_public_key}",
            "ttl": 3600,
        },
        "dmarc": {
            "type": "TXT",
            "name": f"_dmarc.{domain_name}",
            "content": f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{domain_name}; pct=100",
            "ttl": 3600,
        },
    }

    created: dict[str, Any] = {"zone_id": zone_id, "records": {}}
    for key, record in records.items():
        created_record = await upsert_record(zone_id, record)
        created["records"][key] = {
            "id": created_record.get("id"),
            "type": created_record.get("type", record["type"]),
            "name": created_record.get("name", record["name"]),
            "content": created_record.get("content", record["content"]),
            "ttl": created_record.get("ttl", record["ttl"]),
            "priority": created_record.get("priority", record.get("priority")),
        }

    return created


def _safe_answers(query: str, record_type: str) -> list[str]:
    try:
        answers = dns.resolver.resolve(query, record_type)
        return [str(item).strip() for item in answers]
    except Exception:
        return []


async def verify_dns_records(domain_name: str, server_ip: str) -> dict[str, bool]:
    mx_expected = f"10 mail.{domain_name}."
    a_expected = server_ip
    spf_expected = f"v=spf1 ip4:{server_ip} mx ~all"
    dkim_host = f"mail._domainkey.{domain_name}"
    dmarc_host = f"_dmarc.{domain_name}"

    mx_records = _safe_answers(domain_name, "MX")
    a_records = _safe_answers(f"mail.{domain_name}", "A")
    spf_records = _safe_answers(domain_name, "TXT")
    dkim_records = _safe_answers(dkim_host, "TXT")
    dmarc_records = _safe_answers(dmarc_host, "TXT")

    mx_ok = any(record.rstrip(".") == mx_expected.rstrip(".") for record in mx_records)
    a_ok = any(record == a_expected for record in a_records)
    spf_ok = any(spf_expected in record.replace('"', "") for record in spf_records)
    dkim_ok = any("v=DKIM1" in record.replace('"', "") for record in dkim_records)
    dmarc_ok = any(
        f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{domain_name}; pct=100" in record.replace('"', "")
        for record in dmarc_records
    )

    all_valid = mx_ok and a_ok and spf_ok and dkim_ok and dmarc_ok
    return {
        "mx": mx_ok,
        "a": a_ok,
        "spf": spf_ok,
        "dkim": dkim_ok,
        "dmarc": dmarc_ok,
        "all_valid": all_valid,
    }
