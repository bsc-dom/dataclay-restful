import inspect
import json
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
def create_pydantic_model_from_activemethods(cls):
    activemethods = get_activemethods(cls)
    models = {}
    for method in activemethods:
        sig = inspect.signature(method)
        parameters = list(sig.parameters.items())[1:]  # Skip the first parameter

        fields = {}
        for name, param in parameters:
            if issubclass(param.annotation, DataClayObject):
                fields[name] = (Optional[UUID], None)
            else:
                try:
                    create_model("TempModel", field=(param.annotation, ...)).model_json_schema()
                except PydanticSchemaGenerationError as e:
                    raise Exception(f"Type {param.annotation} is not serializable.") from e
                fields[name] = (Optional[param.annotation], None)

        model_config = ConfigDict(arbitrary_types_allowed=True)
        model = create_model(f"{method.__name__}_Model", **fields, __config__=model_config)
        models[method.__name__] = model

    return models


def create_pydantic_model_from_class(cls: Type) -> BaseModel:
    annotations = get_type_hints(cls)
    fields = {}
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


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, DataClayObject):
            return str(obj._dc_meta.id)
        # elif isinstance(obj, UUID):
        #     return str(obj)
        return super().default(obj)


def generate_routes_for_class(cls: DataClayObject) -> APIRouter:
    router = APIRouter()
    ClassModel = create_pydantic_model_from_class(cls)
    activemethod_models = create_pydantic_model_from_activemethods(cls)

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

        try:
            properties = item.get_properties()
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to retrieve person properties.")
        # print(json.dumps(properties, cls=CustomEncoder, indent=2))
        # NOTE: Maybe use "inspect" to mirror the way is done to create ClassBaseModel
        return json.loads(json.dumps(properties, cls=CustomEncoder))

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
        attribute_value = getattr(item, attribute)
        return json.loads(json.dumps(attribute_value, cls=CustomEncoder))

    @router.patch("/{id}")
    async def update_item(id: UUID, item_in: ClassModel) -> Any:
        try:
            item = cls.get_by_id(id)
        except DoesNotExistError as e:
            raise HTTPException(
                status_code=404, detail=f"{cls.__name__} with UUID {id} does not exist."
            )

        body_dict = item_in.model_dump(exclude_unset=True, by_alias=True)

        # TODO: Make it more simple. Maybe use tags in the Pydantic model
        annotations = get_type_hints(cls)
        for name, value in annotations.items():
            name = DC_PROPERTY_PREFIX + name
            if issubclass(value, DataClayObject):
                try:
                    body_dict[name] = value.get_by_id(body_dict[name])
                except DoesNotExistError as e:
                    raise HTTPException(
                        status_code=404,
                        detail=f"{value.__name__} with UUID {body_dict[name]} does not exist.",
                    )

        item.dc_update_properties(body_dict)
        return {"message": "Attribute updated successfully."}

    def create_route(method_name: str, MethodModel: BaseModel):
        @router.post(f"/{{id}}/{method_name}", name=method_name, response_model=Any)
        async def call_item_method(id: UUID, body: MethodModel):
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

            # Looking for DataClayObject parameters to convert the UUIDS
            sig = inspect.signature(method)
            # Don't skip the first parameter because the method is already bound to the object
            parameters = list(sig.parameters.items())
            body_dict = body.dict()
            for name, param in parameters:
                if issubclass(param.annotation, DataClayObject):
                    try:
                        body_dict[name] = param.annotation.get_by_id(body_dict[name])
                    except DoesNotExistError as e:
                        raise HTTPException(
                            status_code=404,
                            detail=f"{param.annotation.__name__} with UUID {body_dict[name]} does not exist.",
                        )
                # TODO: Handle nested types with DataClayObject

            result = method(**body_dict)
            return result

        return call_item_method

    # Create a route for each activemethod
    for method_name, MethodModel in activemethod_models.items():
        create_route(method_name, MethodModel)
        # TODO: I think this is not necessary
        # router.post(f"/{{id}}/{method_name}", name=method_name, response_model=Any)(route_function)

    return router
