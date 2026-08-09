import uuid

from pydantic import BaseModel, ConfigDict


class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_id: str
    name: str
