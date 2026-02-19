from fastapi import APIRouter

from app.api.v1.endpoints.user_endpoints import router as user_router
from app.api.v1.endpoints.health_endpoints import router as health_router
from app.api.v1.endpoints.ekyc_endpoints import router as ekyc_router

routers = APIRouter()
router_list = [user_router, health_router, ekyc_router]

for router in router_list:
    routers.include_router(router)
