from typing import AsyncGenerator

from starlette.requests import Request
from dataclay import Client


async def get_dc_client(
    request: Request,
) -> AsyncGenerator[Client, None]:  # pragma: no cover

    return request.app.state.dc_client
