from pydantic import BaseModel, Field


class UploadPhotosResponse(BaseModel):
    left_face_urls: list[str] = Field(
        ..., description="URLs of the 3 uploaded left face photos"
    )
    right_face_urls: list[str] = Field(
        ..., description="URLs of the 3 uploaded right face photos"
    )
    front_face_urls: list[str] = Field(
        ..., description="URLs of the 3 uploaded front face photos"
    )
    session_id: str = Field(..., description="Unique session ID for the eKYC process")
