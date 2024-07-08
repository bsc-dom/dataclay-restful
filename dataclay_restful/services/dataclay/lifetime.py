from fastapi import FastAPI

from dataclay_restful.settings import settings
from dataclay import Client
from dataclay.metadata.api import MetadataAPI


def init_dc_client(app: FastAPI) -> None:  # pragma: no cover
    """
    Initializes the DataClay client.
    """
    metadata_api = MetadataAPI(settings.redis_host, settings.redis_port)

    # TODO: Split in `dataclay.client.api.Client` the instantiation
    # and initialization (runtime.start) of the runtime, in order to
    # allow modification of the runtime attributes like swapping the metadata
    # service by the metadata API.

    dc_client = Client(settings.mds_host, settings.mds_port)
    dc_client.start()
    dc_client.runtime.metadata_service = metadata_api
    app.state.dc_client = dc_client


async def shutdown_dc_client(app: FastAPI) -> None:  # pragma: no cover
    """
    Closes the DataClay client.
    """
    await app.state.dc_client.stop()
