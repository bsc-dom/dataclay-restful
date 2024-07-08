import json
from typing import Any
from fastapi import APIRouter, HTTPException


import logging
from uuid import UUID
from fastapi import APIRouter
from fastapi.param_functions import Depends
from dataclay_restful.services.metadata_service.dependency import get_mds
from dataclay_restful.services.dataclay.dependency import get_dc_client
from dataclay_restful.web.api.Person.schema import PersonBase

from dataclay.metadata.api import MetadataAPI

from dataclay.metadata.kvdata import ObjectMetadata
from dataclay.exceptions import DoesNotExistError
from dataclay.contrib.modeltest.family import Person
from dataclay.dataclay_object import DataClayObject

from dataclay.config import session_var


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def read_persons(mds: MetadataAPI = Depends(get_mds)) -> dict[UUID, ObjectMetadata]:
    """
    Retrieve all persons metadata.
    """
    return await mds.get_all_objects(filter_func=lambda x: "Person" in x.class_name)


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, DataClayObject):
            return obj.getID()
        # elif isinstance(obj, UUID):
        #     return str(obj)
        return super().default(obj)


@router.get("/{uuid}")
async def read_person(id: UUID) -> Any:
    """
    Retrieve a person by UUID.
    """
    # TODO: What should we do with unserializable objects? Maybe just return a pickled object?

    try:
        person = Person.get_by_id(id)
    except DoesNotExistError as e:
        raise HTTPException(status_code=404, detail=f"Person with UUID {id} does not exist.")

    try:
        properties = person.get_properties()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve person properties.")
    print(json.dumps(properties, cls=CustomEncoder, indent=2))
    return json.dumps(properties, cls=CustomEncoder)


@router.get("/{uuid}/{attribute}")
async def read_person_attribute(id: UUID, attribute: str) -> Any:
    """
    Retrieve the value of an attribute for a person by UUID.
    """
    # TODO: Improve the session handling with contextvars
    session_var.set(
        {
            "dataset_name": "admin",
            "username": "admin",
            "token": "admin",
        }
    )

    try:
        person = Person.get_by_id(id)
    except DoesNotExistError as e:
        raise HTTPException(status_code=404, detail=f"Person with UUID {id} does not exist.")

    try:
        attribute_value = getattr(person, attribute)
    except AttributeError:
        raise HTTPException(
            status_code=400, detail=f"Attribute '{attribute}' does not exist in Person object."
        )

    # If the attribute is a DataClayObject, return its ID
    # TODO: It will fail if the returned object is more complex, with nested DataClayObjects.
    # Maybe use json/pickle to serialize the object?
    if isinstance(attribute_value, DataClayObject):
        return attribute_value.getID()
    else:
        return attribute_value


@router.put("/{uuid}")
async def update_person_attribute(id: UUID, update_request: PersonBase) -> Any:
    """
    Update the attributes of a person by UUID.
    """
    # TODO: Improve the session handling with contextvars
    session_var.set(
        {
            "dataset_name": "admin",
            "username": "admin",
            "token": "admin",
        }
    )

    try:
        person = Person.get_by_id(id)
    except DoesNotExistError as e:
        raise HTTPException(status_code=404, detail=f"Person with UUID {id} does not exist.")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

    try:
        # TODO: Allow to update DataClayObject attributes using their UUID.
        # We should first retrieve the object attribute by its UUID and then update the current object attribute.
        person.dc_update_properties(update_request.model_dump(exclude_unset=True, by_alias=True))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update attribute value.")

    return {"message": "Attribute updated successfully."}


@router.post("/{uuid}/{method}")
async def call_person_method(id: UUID, method: str) -> Any:
    """
    Call a method of a person by UUID.
    """
    # TODO: Improve the session handling with contextvars
    session_var.set(
        {
            "dataset_name": "admin",
            "username": "admin",
            "token": "admin",
        }
    )

    try:
        person = Person.get_by_id(id)
    except DoesNotExistError as e:
        raise HTTPException(status_code=404, detail=f"Person with UUID {id} does not exist.")

    try:
        value = getattr(person, method)()
    except AttributeError:
        raise HTTPException(
            status_code=400, detail=f"Method '{method}' does not exist in Person object."
        )

    return value
