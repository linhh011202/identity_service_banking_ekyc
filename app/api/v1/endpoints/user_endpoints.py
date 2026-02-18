from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.container import Container
from app.dto.base_response import BaseResponse
from app.dto.user.request.get_user_request import GetUserRequest
from app.dto.user.request.register_request import RegisterRequest
from app.dto.user.response.get_user_response import GetUserResponse
from app.dto.user.response.login_response import LoginResponse
from app.dto.user.response.register_response import RegisterResponse
from app.service.user_service import UserService
from app.dto.user.request.login_request import LoginRequest


router = APIRouter(prefix="/user", tags=["user"])


@router.post("/get-by-email", response_model=BaseResponse[GetUserResponse])
@inject
def get_user_by_email(
    request: GetUserRequest,
    user_service: UserService = Depends(Provide[Container.user_service]),
) -> BaseResponse[GetUserResponse] | JSONResponse:
    user, err = user_service.get_user_by_email(request.email)
    if err:
        return JSONResponse(
            status_code=err.http_status,
            content=BaseResponse.error_response(
                code=err.code, message=err.message
            ).model_dump(),
        )

    user_data = GetUserResponse.model_validate(user)
    return BaseResponse.success_response(
        data=user_data, message="User retrieved successfully"
    )


@router.post("/register", response_model=BaseResponse[RegisterResponse])
@inject
def register_user(
    request: RegisterRequest,
    user_service: UserService = Depends(Provide[Container.user_service]),
) -> BaseResponse[RegisterResponse] | JSONResponse:
    user, err = user_service.register_user(
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        phone_number=request.phone_number,
    )
    if err:
        return JSONResponse(
            status_code=err.http_status,
            content=BaseResponse.error_response(
                code=err.code, message=err.message
            ).model_dump(),
        )
    return BaseResponse.success_response(
        data=RegisterResponse.model_validate(user),
        message="User registered successfully",
    )


@router.post("/login", response_model=BaseResponse[LoginResponse])
@inject
def login(
    request: LoginRequest,
    user_service: UserService = Depends(Provide[Container.user_service]),
) -> BaseResponse[LoginResponse] | JSONResponse:
    user, err = user_service.login(request.email, request.password)
    if err:
        return JSONResponse(
            status_code=err.http_status,
            content=BaseResponse.error_response(
                code=err.code, message=err.message
            ).model_dump(),
        )
    return BaseResponse.success_response(
        data=LoginResponse.model_validate(user),
        message="Login successful",
    )
