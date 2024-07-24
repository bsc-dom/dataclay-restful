import inspect
from typing import Any, Optional, Type, get_type_hints
from fastapi import APIRouter, HTTPException


import logging
from uuid import UUID
from fastapi import APIRouter
from fastapi.param_functions import Depends
from pydantic import BaseModel, ConfigDict
from dataclay_restful.services.metadata_service.dependency import get_mds


from dataclay.metadata.api import MetadataAPI

from dataclay.metadata.kvdata import ObjectMetadata
from dataclay.exceptions import DoesNotExistError
from dataclay.dataclay_object import DataClayObject
from pydantic import AliasGenerator, BaseModel, ConfigDict, create_model
from dataclay.config import session_var
from dataclay.dataclay_object import DC_PROPERTY_PREFIX
from pydantic.errors import PydanticSchemaGenerationError

logger = logging.getLogger(__name__)

router = APIRouter()


# Function to get activemethods
def get_activemethods(cls) -> list[inspect.Signature]:
    return [
        method
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction)
        if getattr(method, "_is_activemethod", False)
    ]


# Function to create Pydantic models for method parameters
def create_models_for_activemethods(cls):
    activemethods = get_activemethods(cls)
    models = {}
    for method in activemethods:
        sig = inspect.signature(method)
        parameters = list(sig.parameters.items())[1:]  # Skip the first parameter
        fields = {
            name: (param.annotation, ...)
            for name, param in parameters
            # NOTE: The following condition is not necessary (maybe)
            # if param.annotation != param.empty and name != "self"
        }
        model_config = ConfigDict(arbitrary_types_allowed=True)
        model = create_model(f"{method.__name__}_Model", **fields, __config__=model_config)
        models[method.__name__] = model

    return models


def create_pydantic_model_from_class(cls: Type) -> BaseModel:
    annotations = get_type_hints(cls)
    fields = {}
    # TODO: May be necessary to define the ClassBase fields in a config file
    # because it may have types that are not serialized, and we need to
    # change them for proper FastAPI documentation. For example these:
    for k, v in annotations.items():
        if issubclass(v, DataClayObject):
            fields[k] = (Optional[UUID], None)
        else:
            # If there is a type that is not serializable, we raise an exception
            try:
                create_model("TempModel", field=(v, ...)).model_json_schema()
            except PydanticSchemaGenerationError as e:
                # TODO: Improve error handling
                raise Exception(f"Type {v} is not serializable.") from e
            fields[k] = (Optional[v], None)

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=lambda field_name: DC_PROPERTY_PREFIX + field_name,
        ),
        arbitrary_types_allowed=True,
    )

    pydantic_model = create_model(cls.__name__ + "Base", **fields, __config__=model_config)
    return pydantic_model


def generate_routes_for_class(cls: DataClayObject) -> APIRouter:
    router = APIRouter()
    PydanticModel = create_pydantic_model_from_class(cls)
    models = create_models_for_activemethods(cls)

    @router.get("/")
    async def read_items(mds: MetadataAPI = Depends(get_mds)) -> list[ObjectMetadata]:
        return (
            await mds.get_all_objects(filter_func=lambda x: cls.__name__ in x.class_name)
        ).values()

    @router.get("/{id}")
    async def read_item(id: UUID) -> Any:
        try:
            item = cls.get_by_id(id)
        except DoesNotExistError as e:
            raise HTTPException(
                status_code=404, detail=f"{cls.__name__} with UUID {id} does not exist."
            )
        return item.get_properties()

    @router.get("/{id}/{attribute}")
    async def read_item_attribute(id: UUID, attribute: str) -> Any:
        # TODO: Improve the session handling with contextvars
        session_var.set(
            {
                "dataset_name": "admin",
                "username": "admin",
                "token": "admin",
            }
        )
        try:
            item = cls.get_by_id(id)
        except DoesNotExistError as e:
            raise HTTPException(
                status_code=404, detail=f"{cls.__name__} with UUID {id} does not exist."
            )
        return getattr(item, attribute)

    @router.patch("/{id}")
    async def update_item(id: UUID, item_in: PydanticModel) -> Any:
        try:
            item = cls.get_by_id(id)
        except DoesNotExistError as e:
            raise HTTPException(
                status_code=404, detail=f"{cls.__name__} with UUID {id} does not exist."
            )
        item.dc_update_properties(item_in.model_dump(exclude_unset=True, by_alias=True))
        return {"message": "Attribute updated successfully."}

    def create_route(method_name: str, model: BaseModel):
        @router.post(f"/{{id}}/{method_name}", name=method_name, response_model=Any)
        async def call_item_method(id: UUID, body: model):
            session_var.set(
                {
                    "dataset_name": "admin",
                    "username": "admin",
                    "token": "admin",
                }
            )
            try:
                item = cls.get_by_id(id)
            except DoesNotExistError:
                raise HTTPException(
                    status_code=404, detail=f"{cls.__name__} with UUID {id} does not exist."
                )

            method = getattr(item, method_name)
            result = method(**body.dict())
            return result

        return call_item_method

    # Create a route for each activemethod
    for method_name, model in models.items():
        create_route(method_name, model)
        # TODO: I think this is not necessary
        # router.post(f"/{{id}}/{method_name}", name=method_name, response_model=Any)(route_function)

    return router
