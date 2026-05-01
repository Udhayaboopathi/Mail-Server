from pathlib import Path

import dkim

from config import settings


async def sign_message(raw_message: bytes, domain: str, selector: str | None = None, private_key_path: str | None = None) -> bytes:
    key_path = Path(private_key_path or settings.dkim_private_key_path)
    if not key_path.exists():
        return raw_message

    signature = dkim.sign(
        message=raw_message,
        selector=(selector or settings.dkim_selector).encode("utf-8"),
        domain=domain.encode("utf-8"),
        privkey=key_path.read_bytes(),
        include_headers=[b"from", b"to", b"subject", b"date", b"mime-version", b"content-type"],
    )
    return signature + raw_message
