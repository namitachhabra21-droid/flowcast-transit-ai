"""Internal ML prediction endpoint: POST /predict.

Called server-to-server by the Node.js/Express backend, not by end users
directly — it's mounted at the app root (not under /api/v1) and isn't
gated by the Clerk/API-key auth used elsewhere in this service, since the
caller here is a trusted internal service, not an org-scoped client. Put
this behind a shared-secret header or network-level restriction (VPC,
internal-only ingress) before it's reachable from anywhere but the Node
backend.

predict_crowding() is a placeholder heuristic standing in for the trained
model, following the same swap-later pattern as app/ml/model.py: replace
its body with a real model.predict(feature_vector) call and keep the
(features, capacity) -> (count, pct, level) signature.
"""
import math
from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

router = APIRouter(tags=["ml"])

MODEL_VERSION = "heuristic-v1"
SANE_MAX_PASSENGER_COUNT = 2000


class WeatherCondition(str, Enum):
    clear = "clear"
    rain = "rain"
    fog = "fog"
    extreme = "extreme"


class CrowdingLevel(str, Enum):
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"


# ---- Request: raw input features only. hour/day_of_week/is_weekend are
# deliberately NOT request fields — they're derived server-side from
# `timestamp` (see build_feature_vector) so the client can't send an
# inconsistent hour/day-of-week/timestamp combination, and so there's one
# fewer thing for the Node layer to compute correctly.
class PredictionRequest(BaseModel):
    route_id: str = Field(..., min_length=1, description="Route identifier, e.g. 'R1'")
    station_id: str = Field(..., min_length=1, description="Stop/station identifier, e.g. 'S12'")
    vehicle_capacity: int = Field(..., gt=0, description="Max passenger capacity of the vehicle")
    current_passenger_count: int = Field(
        ..., ge=0, description="Latest known ticket/sensor count for this vehicle right now"
    )
    timestamp: datetime = Field(..., description="ISO 8601 timestamp to predict for")
    is_holiday: bool = Field(False, description="Whether `timestamp`'s date is a public holiday")
    weather_condition: Optional[WeatherCondition] = Field(
        None, description="Optional — omit if unknown; treated as 'unknown' in the model"
    )

    @field_validator("current_passenger_count")
    @classmethod
    def _sane_upper_bound(cls, v: int) -> int:
        if v > SANE_MAX_PASSENGER_COUNT:
            raise ValueError(f"current_passenger_count exceeds sane upper bound ({SANE_MAX_PASSENGER_COUNT})")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "route_id": "R1",
                "station_id": "S12",
                "vehicle_capacity": 60,
                "current_passenger_count": 42,
                "timestamp": "2026-08-10T08:15:00+05:30",
                "is_holiday": False,
                "weather_condition": "clear",
            }
        }


class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    route_id: str
    station_id: str
    timestamp: datetime
    predicted_passenger_count: int
    predicted_occupancy_percentage: float
    crowding_level: CrowdingLevel
    model_version: str


def build_feature_vector(req: PredictionRequest) -> dict:
    """Raw inputs -> derived features -> the dict shape the model consumes."""
    hour = req.timestamp.hour
    day_of_week = req.timestamp.weekday()  # 0=Mon .. 6=Sun
    return {
        "route_id": req.route_id,
        "station_id": req.station_id,
        "hour": hour,
        "hour_sin": math.sin(2 * math.pi * hour / 24),
        "hour_cos": math.cos(2 * math.pi * hour / 24),
        "day_of_week": day_of_week,
        "is_weekend": day_of_week >= 5,
        "is_holiday": req.is_holiday,
        "occupancy_ratio": req.current_passenger_count / req.vehicle_capacity,
        "weather_condition": req.weather_condition.value if req.weather_condition else "unknown",
    }


def predict_crowding(features: dict, capacity: int) -> tuple:
    """base occupancy x time-of-day peak x weekend/holiday damping — same
    heuristic shape as app/ml/model.py. Swap this body for a real model
    call; build_feature_vector's output is already the feature dict a
    trained model would take."""
    peak_multiplier = 1.3 if features["hour"] in (8, 9, 18, 19) else 1.0
    calm_multiplier = 0.7 if features["is_weekend"] or features["is_holiday"] else 1.0

    predicted_ratio = min(1.3, features["occupancy_ratio"] * peak_multiplier * calm_multiplier)
    predicted_count = round(predicted_ratio * capacity)
    occupancy_pct = round(predicted_ratio * 100, 1)

    if occupancy_pct <= 40:
        level = CrowdingLevel.low
    elif occupancy_pct <= 75:
        level = CrowdingLevel.medium
    else:
        level = CrowdingLevel.high

    return predicted_count, occupancy_pct, level


@router.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest) -> PredictionResponse:
    try:
        features = build_feature_vector(payload)
        predicted_count, occupancy_pct, level = predict_crowding(features, payload.vehicle_capacity)
    except Exception as exc:  # model/feature-building failure, not a validation error
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")

    return PredictionResponse(
        route_id=payload.route_id,
        station_id=payload.station_id,
        timestamp=payload.timestamp,
        predicted_passenger_count=predicted_count,
        predicted_occupancy_percentage=occupancy_pct,
        crowding_level=level,
        model_version=MODEL_VERSION,
    )
