from typing import List

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse

from app.core.container import Container
from app.dto.base_response import BaseResponse
from app.dto.ekyc.response.upload_photos_response import UploadPhotosResponse
from app.service.ekyc_service import EkycService
from app.service.pubsub_service import PubsubService
from app.util.security import verify_access_token

router = APIRouter(prefix="/ekyc", tags=["ekyc"])


@router.post("/upload-photos", response_model=BaseResponse[UploadPhotosResponse])
@inject
async def upload_photos(
    left_faces: List[UploadFile] = File(..., description="3 left face photos"),
    right_faces: List[UploadFile] = File(..., description="3 right face photos"),
    front_faces: List[UploadFile] = File(..., description="3 front face photos"),
    user_email: str = Depends(verify_access_token),
    ekyc_service: EkycService = Depends(Provide[Container.ekyc_service]),
    pubsub_service: PubsubService = Depends(Provide[Container.pubsub_service]),
) -> BaseResponse[UploadPhotosResponse] | JSONResponse:
    result, err = await ekyc_service.upload_photos(
        user_email=user_email,
        left_faces=left_faces,
        right_faces=right_faces,
        front_faces=front_faces,
    )
    if err:
        return JSONResponse(
            status_code=err.http_status if hasattr(err, "http_status") else 400,
            content=BaseResponse.error_response(
                code=err.code, message=err.message
            ).model_dump(),
        )

    # Fire-and-forget: publish sign-up event to Pub/Sub
    pubsub_service.publish_signup_event(email=user_email)

    return BaseResponse.success_response(
        data=result, message="Photos uploaded successfully"
    )
