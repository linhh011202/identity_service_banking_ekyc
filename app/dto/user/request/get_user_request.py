from pydantic import BaseModel, Field


class GetUserRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Username to search for")
