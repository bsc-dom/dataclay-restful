from fastapi.routing import APIRouter

from dataclay_restful.web.api import echo, monitoring, resources

from dataclay_restful.web.api.dynamic.views import generate_routes_for_class
from dataclay.utils import get_class_by_name
import rest_config

api_router = APIRouter()
api_router.include_router(monitoring.router)
api_router.include_router(echo.router, prefix="/echo", tags=["echo"])
api_router.include_router(resources.router, prefix="/resources", tags=["resources"])

# Dynamic router generation
for class_name, tag in rest_config.class_names.items():
    cls = get_class_by_name(class_name)
    router = generate_routes_for_class(cls)
    api_router.include_router(router, prefix=f"/{tag.lower()}", tags=[tag])
