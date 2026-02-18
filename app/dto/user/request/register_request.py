from typing import Optional

from pydantic import BaseModel, Field, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, max_length=128, description="Password")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
