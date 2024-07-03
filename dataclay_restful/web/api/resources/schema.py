from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class BackendDTO(BaseModel):
    id: UUID
    host: str
    port: int
    dataclay_id: UUID
