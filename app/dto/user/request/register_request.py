from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="New username")
    password: str = Field(..., min_length=6, max_length=128, description="New password")
