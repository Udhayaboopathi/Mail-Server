import asyncio
from pathlib import Path

import bleach
from sqlalchemy.ext.asyncio import AsyncSession


class SpamService:
    @staticmethod
    async def sanitize_html(html: str | None) -> str | None:
        if html is None:
            return None
        return bleach.clean(html, tags=bleach.sanitizer.ALLOWED_TAGS, attributes=bleach.sanitizer.ALLOWED_ATTRIBUTES, strip=True)

    @staticmethod
    async def run_spamassassin(raw_message: bytes, host: str) -> tuple[bytes, dict[str, str]]:
        process = await asyncio.create_subprocess_exec(
            "spamc",
            "-d",
            host,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate(raw_message)
        headers = {"X-Spam-Checked": "yes"}
        return stdout or raw_message, headers
