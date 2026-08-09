from datetime import datetime
from typing import List

from pydantic import BaseModel


class TripStopOut(BaseModel):
    id: str
    name: str
    scheduled_time: datetime


class TripOut(BaseModel):
    id: str
    route_id: str
    route_name: str
    departure_time: datetime
    stops: List[TripStopOut]
