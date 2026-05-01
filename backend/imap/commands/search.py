from imap.session import IMAPSession


async def handle_search(session: IMAPSession, tag: str, args: str) -> None:
    await session.search(tag, args)
