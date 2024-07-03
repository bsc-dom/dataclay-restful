from fastapi import FastAPI

from dataclay_restful.settings import settings
from dataclay.metadata.api import MetadataAPI


def init_mds(app: FastAPI) -> None:  # pragma: no cover
    """
    Creates connection pool for redis.

    :param app: current fastapi application.
    """

    app.state.mds = MetadataAPI(settings.redis_host, settings.redis_port)


async def shutdown_mds(app: FastAPI) -> None:  # pragma: no cover
    """
    Closes redis connection pool.

    :param app: current FastAPI app.
    """
    await app.state.mds.close()
