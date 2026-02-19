from typing import Optional

from pydantic import BaseModel


class LoginResponse(BaseModel):
    email: Optional[str]
    access_token: str
    token_type: str = "bearer"

    class Config:
        from_attributes = True
