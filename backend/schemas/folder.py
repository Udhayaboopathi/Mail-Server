from pydantic import BaseModel


class FolderListResponse(BaseModel):
    folders: list[str]

class FolderCreateRequest(BaseModel):
    name: str

class FolderRenameRequest(BaseModel):
    name: str
