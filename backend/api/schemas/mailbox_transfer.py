from pydantic import BaseModel


class MailboxImportMboxResult(BaseModel):
    imported: int
    failed: int
    skipped_duplicates: int


class MailboxImportZipResult(BaseModel):
    imported: int
    failed: int
