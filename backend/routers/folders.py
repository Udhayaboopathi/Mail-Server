from fastapi import APIRouter, Depends

from deps import get_current_user
from schemas.common import ActionResponse
from schemas.folder import FolderCreateRequest, FolderListResponse, FolderRenameRequest
from models.user import User

router = APIRouter(prefix="/api/folders", tags=["folders"])


@router.get("", response_model=FolderListResponse)
async def list_folders(_: User = Depends(get_current_user)) -> FolderListResponse:
    return FolderListResponse(folders=["Inbox", "Sent", "Drafts", "Trash", "Spam"])


@router.post("", response_model=ActionResponse)
async def create_folder(payload: FolderCreateRequest, _: User = Depends(get_current_user)) -> ActionResponse:
    return ActionResponse(status="created")


@router.patch("/{folder_name}", response_model=ActionResponse)
async def rename_folder(folder_name: str, payload: FolderRenameRequest, _: User = Depends(get_current_user)) -> ActionResponse:
    return ActionResponse(status="renamed")


@router.delete("/{folder_name}", response_model=ActionResponse)
async def delete_folder(folder_name: str, _: User = Depends(get_current_user)) -> ActionResponse:
    return ActionResponse(status="deleted")
