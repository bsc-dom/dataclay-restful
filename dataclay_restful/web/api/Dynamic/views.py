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

    print(fields)

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

    @router.get("/")
    async def read_items(mds: MetadataAPI = Depends(get_mds)) -> list[ObjectMetadata]:
        return (
            await mds.get_all_objects(filter_func=lambda x: cls.__name__ in x.class_name)
        ).values()

    @router.get("/{uuid}")
    async def read_item(id: UUID) -> Any:
        try:
            item = cls.get_by_id(id)
        except DoesNotExistError as e:
            raise HTTPException(
                status_code=404, detail=f"{cls.__name__} with UUID {id} does not exist."
            )
        return item.get_properties()

    @router.get("/{uuid}/{attribute}")
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

    @router.patch("/{uuid}")
    async def update_item(id: UUID, item_in: PydanticModel) -> Any:
        try:
            item = cls.get_by_id(id)
        except DoesNotExistError as e:
            raise HTTPException(
                status_code=404, detail=f"{cls.__name__} with UUID {id} does not exist."
            )
        item.dc_update_properties(item_in.model_dump(exclude_unset=True, by_alias=True))
        return {"message": "Attribute updated successfully."}

    @router.post("/{uuid}/{method}")
    async def call_item_method(id: UUID, method: str) -> Any:
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
        return getattr(item, method)()

    return router
