from fastapi import APIRouter, Depends

from deps import get_current_user
from models.user import User
from schemas.mail import SearchResponse

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(q: str, _: User = Depends(get_current_user)) -> SearchResponse:
    return SearchResponse(results=[])
