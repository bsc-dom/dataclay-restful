from typing import AsyncGenerator

from starlette.requests import Request
from dataclay.metadata.api import MetadataAPI


async def get_mds(
    request: Request,
) -> AsyncGenerator[MetadataAPI, None]:  # pragma: no cover

    return request.app.state.mds
