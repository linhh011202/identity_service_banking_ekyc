from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.container import Container
from app.dto.base_response import BaseResponse
from app.dto.ekyc.request.login_request import LoginRequest
from app.dto.ekyc.request.upload_photos_request import UploadPhotosRequest
from app.dto.ekyc.response.login_response import LoginResponse
from app.dto.ekyc.response.upload_photos_response import UploadPhotosResponse
from app.service.ekyc.ekyc_service import EkycService
from app.util.security import verify_access_token

router = APIRouter(prefix="/ekyc", tags=["ekyc"])


@router.post("/upload-photos", response_model=BaseResponse[UploadPhotosResponse])
@inject
async def upload_photos(
    request: UploadPhotosRequest = Depends(),
    user_email: str = Depends(verify_access_token),
    ekyc_service: EkycService = Depends(Provide[Container.ekyc_service]),
) -> BaseResponse[UploadPhotosResponse] | JSONResponse:
    result, err = await ekyc_service.upload_photos(
        user_email=user_email,
        left_faces=request.left_faces,
        right_faces=request.right_faces,
        front_faces=request.front_faces,
        fcm_token=request.fcm_token,
    )
    if err:
        return JSONResponse(
            status_code=err.http_status if hasattr(err, "http_status") else 400,
            content=BaseResponse.error_response(
                code=err.code, message=err.message
            ).model_dump(),
        )

    return BaseResponse.success_response(
        data=UploadPhotosResponse(session_id=result.session_id),
        message="Photos uploaded successfully",
    )


@router.post("/login", response_model=BaseResponse[LoginResponse])
@inject
async def login(
    request: LoginRequest = Depends(),
    ekyc_service: EkycService = Depends(Provide[Container.ekyc_service]),
) -> BaseResponse[LoginResponse] | JSONResponse:
    result, err = await ekyc_service.login(
        user_email=request.email,
        faces=request.faces,
        fcm_token=request.fcm_token,
    )
    if err:
        return JSONResponse(
            status_code=err.http_status if hasattr(err, "http_status") else 400,
            content=BaseResponse.error_response(
                code=err.code, message=err.message
            ).model_dump(),
        )

    return BaseResponse.success_response(
        data=LoginResponse(session_id=result.session_id),
        message="Login event published successfully",
    )
