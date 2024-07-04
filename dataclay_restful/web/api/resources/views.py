import logging
from typing import Any
from uuid import UUID
from fastapi import APIRouter
from fastapi.param_functions import Depends
from dataclay_restful.services.metadata_service.dependency import get_mds


from dataclay.metadata.api import MetadataAPI
from dataclay.metadata.kvdata import Backend


logger = logging.getLogger(__name__)


router = APIRouter()


@router.get("/backends", response_model=Any)
async def read_backends(
    mds: MetadataAPI = Depends(get_mds),
) -> dict[UUID, Backend]:
    """
    Retrieve all backends.
    """
    return await mds.get_all_backends()
