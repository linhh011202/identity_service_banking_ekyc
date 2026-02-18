from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    success: bool = Field(..., description="Whether the request was successful")
    code: int = Field(..., description="Response code")
    message: str = Field(..., description="Response message")
    data: T | None = Field(None, description="Response data")

    @classmethod
    def success_response(cls, data: T, message: str = "Success", code: int = 0):
        return cls(success=True, code=code, message=message, data=data)

    @classmethod
    def error_response(cls, code: int, message: str):
        return cls(success=False, code=code, message=message, data=None)
