from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict


class CrowdingStopOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    stop_id: str
    stop_name: str
    scheduled_time: datetime
    score: float
    level: str
    model_version: str


class TripCrowdingOut(BaseModel):
    trip_id: str
    route_id: str
    generated_at: datetime
    stops: List[CrowdingStopOut]
