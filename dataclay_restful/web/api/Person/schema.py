from fastapi import APIRouter, HTTPException, Depends
from pydantic import AliasGenerator, BaseModel, ConfigDict, create_model
from typing import Any, Dict, Optional, Type
from uuid import UUID

from dataclay.contrib.modeltest.family import Person, Dog
from dataclay.dataclay_object import DC_PROPERTY_PREFIX


# TODO: Create PersonBase from Person class dynamically
# def create_pydantic_model_from_class(cls: Type) -> BaseModel:
#     annotations = cls.__annotations__
#     fields = {k: (v, None) for k, v in annotations.items()}
#     pydantic_model = create_model(
#         cls.__name__ + "Model", **fields, __config__={"arbitrary_types_allowed": True}
#     )
#     return pydantic_model


# PersonBase = create_pydantic_model_from_class(Person)


class PersonBase(BaseModel):

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=lambda field_name: DC_PROPERTY_PREFIX + field_name,
        )
    )

    name: Optional[str] = None
    age: Optional[int] = None
    spouse: Optional[UUID] = None
    dog: Optional[UUID] = None


class PersonCreate(BaseModel):
    name: str
    age: int


class MakePersistent(BaseModel):
    alias: Optional[str] = None
    backend_id: Optional[str] = None
