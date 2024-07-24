from fastapi.routing import APIRouter

from dataclay_restful.web.api import echo, monitoring, resources

api_router = APIRouter()
api_router.include_router(monitoring.router)
api_router.include_router(echo.router, prefix="/echo", tags=["echo"])
api_router.include_router(resources.router, prefix="/resources", tags=["resources"])
# api_router.include_router(Person.router, prefix="/Person", tags=["Person"])


# Dynamic router generation

from dataclay_restful.web.api.Dynamic.views import generate_routes_for_class
from dataclay.utils import get_class_by_name

# TODO: Define classes in config file
for class_name in (
    "dataclay.contrib.modeltest.apirest.Product",
    # "dataclay.contrib.modeltest.family.Person",
    # "dataclay.contrib.modeltest.family.Dog",
    # "dataclay.contrib.modeltest.classes.Dog",
    # "dataclay.contrib.modeltest.classes.Police",
    # "dataclay.contrib.modeltest.classes.Criminal",
):
    cls = get_class_by_name(class_name)
    router = generate_routes_for_class(cls)
    print(class_name)
    print(router)
    api_router.include_router(
        router, prefix=f"/{class_name.lower()}", tags=[class_name.split(".")[-1]]
    )
