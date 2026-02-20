from pydantic import BaseModel, Field


class LoginResponse(BaseModel):
    session_id: str = Field(..., description="Unique session ID for the eKYC login")
