from pydantic import BaseModel, Field


class UploadPhotosResponse(BaseModel):
    session_id: str = Field(..., description="Unique session ID for the eKYC process")
