from pydantic import BaseModel


class LoginResponse(BaseModel):
    username: str

    class Config:
        from_attributes = True
