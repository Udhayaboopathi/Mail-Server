from imap.session import IMAPSession


async def handle_fetch(session: IMAPSession, tag: str, args: str) -> None:
    await session.fetch(tag, args)
