from fastapi.routing import APIRouter

from dataclay_restful.web.api import echo, monitoring, resources

api_router = APIRouter()
api_router.include_router(monitoring.router)
api_router.include_router(echo.router, prefix="/echo", tags=["echo"])
api_router.include_router(resources.router, prefix="/resources", tags=["resources"])
