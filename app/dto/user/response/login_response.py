from typing import Optional

from pydantic import BaseModel


class LoginResponse(BaseModel):
    email: Optional[str]

    class Config:
        from_attributes = True
