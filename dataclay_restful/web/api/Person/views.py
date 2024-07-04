from fastapi import APIRouter, HTTPException


import logging
from uuid import UUID
from fastapi import APIRouter
from fastapi.param_functions import Depends
from dataclay_restful.services.metadata_service.dependency import get_mds


from dataclay.metadata.api import MetadataAPI

from dataclay.metadata.kvdata import ObjectMetadata
from dataclay.exceptions import DoesNotExistError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def read_persons(mds: MetadataAPI = Depends(get_mds)) -> dict[UUID, ObjectMetadata]:
    """
    Retrieve all persons.
    """
    return await mds.get_all_objects(filter_func=lambda x: "Person" in x.class_name)


@router.get("/{uuid}")
async def read_person(id: UUID, mds: MetadataAPI = Depends(get_mds)) -> ObjectMetadata:
    """
    Retrieve a person by UUID.
    """
    try:
        return await mds.get_object_md_by_id(id)
    except DoesNotExistError as e:
        raise HTTPException(status_code=404, detail=f"Person with UUID {id} does not exist.")
    except Exception as e:
        # Log the exception if needed
        raise HTTPException(status_code=500, detail="Internal Server Error")
