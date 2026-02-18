import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GetUserResponse(BaseModel):
    id: uuid.UUID
    email: Optional[str]
    phone_number: Optional[str]
    full_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
