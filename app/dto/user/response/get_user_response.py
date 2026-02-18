from datetime import datetime

from pydantic import BaseModel


class GetUserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
