from pydantic import BaseModel, Field, EmailStr


class GetUserRequest(BaseModel):
    email: EmailStr = Field(..., description="Email to search for")
