from __future__ import annotations


def generate_dns_guide(
    domain_name: str,
    server_ip: str,
    dkim_public_key: str,
    dkim_selector: str = "mail",
) -> dict:
    return {
        "domain": domain_name,
        "records": [
            {
                "type": "MX",
                "name": "@",
                "value": f"mail.{domain_name}",
                "priority": "10",
                "ttl": "3600",
                "purpose": "Tells the internet which server handles email for this domain",
            },
            {
                "type": "A",
                "name": f"mail.{domain_name}",
                "value": server_ip,
                "priority": "-",
                "ttl": "3600",
                "purpose": "Points the mail hostname to your server IP",
            },
            {
                "type": "TXT",
                "name": "@",
                "value": f"v=spf1 ip4:{server_ip} mx ~all",
                "priority": "-",
                "ttl": "3600",
                "purpose": "SPF: authorises your server to send email for this domain",
            },
            {
                "type": "TXT",
                "name": f"{dkim_selector}._domainkey.{domain_name}",
                "value": f"v=DKIM1; k=rsa; p={dkim_public_key}",
                "priority": "-",
                "ttl": "3600",
                "purpose": "DKIM: cryptographic signature so recipients trust your emails",
            },
            {
                "type": "TXT",
                "name": f"_dmarc.{domain_name}",
                "value": f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{domain_name}; pct=100",
                "priority": "-",
                "ttl": "3600",
                "purpose": "DMARC: policy for what to do when SPF/DKIM fail",
            },
        ],
        "ptr_note": f"Set reverse DNS (PTR) for {server_ip} -> mail.{domain_name} in your VPS provider control panel (not in Cloudflare)",
        "propagation_note": "DNS changes take 5-30 minutes on Cloudflare. Other providers may take up to 48 hours.",
        "verify_commands": {
            "mx": f"dig MX {domain_name}",
            "spf": f"dig TXT {domain_name}",
            "dkim": f"dig TXT {dkim_selector}._domainkey.{domain_name}",
            "dmarc": f"dig TXT _dmarc.{domain_name}",
            "a": f"dig A mail.{domain_name}",
        },
    }
