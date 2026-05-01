from __future__ import annotations

import asyncio
import ssl

from config import settings
from imap.session import IMAPSession


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    session = IMAPSession(reader=reader, writer=writer)
    await session.run()


async def create_imap_server() -> None:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile="/etc/ssl/certs/mail.crt", keyfile="/etc/ssl/private/mail.key")
    server = await asyncio.start_server(handle_client, host="0.0.0.0", port=993, ssl=context)
    async with server:
        await server.serve_forever()
