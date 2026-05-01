from pydantic import BaseModel


class ActionResponse(BaseModel):
    status: str
    detail: str | None = None
