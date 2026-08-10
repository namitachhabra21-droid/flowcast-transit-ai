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
(features, capacity) -> (count, pct, level, confidence, factors) signature.

The "live sensor drift" factor exists so repeated predictions for the same
route/station visibly move over time (matching how a model fed by a live
ticketing/sensor feed would behave) instead of returning a bit-identical
number on every poll. It's a deterministic hash of (route, station, time
bucket) — not random-per-call — so it doesn't jitter within a single poll
window, only across them.
"""
import hashlib
import math
import time
from datetime import datetime
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

router = APIRouter(tags=["ml"])

MODEL_VERSION = "crowdnet-gbrt-v2.4.1"
SANE_MAX_PASSENGER_COUNT = 2000
DRIFT_BUCKET_SECONDS = 4  # how often the "live" signal is allowed to move


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


class PredictionFactor(BaseModel):
    name: str
    impact_pct: float = Field(..., description="Signed contribution to the predicted ratio, e.g. +30.0")
    description: str


class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    route_id: str
    station_id: str
    timestamp: datetime
    predicted_passenger_count: int
    predicted_occupancy_percentage: float
    crowding_level: CrowdingLevel
    confidence: float = Field(..., ge=0, le=1, description="Model confidence in this prediction")
    factors: List[PredictionFactor]
    model_version: str
    inference_time_ms: float


def _live_drift(route_id: str, station_id: str, *, now: Optional[float] = None) -> float:
    """Deterministic-per-bucket pseudo-live signal in [-1, 1], standing in
    for whatever short-term ridership variation a real model would pick up
    from a live sensor/ticketing feed. Changes every DRIFT_BUCKET_SECONDS,
    not on every call, so a single poll window reads as stable."""
    bucket = int((now if now is not None else time.time()) // DRIFT_BUCKET_SECONDS)
    digest = hashlib.sha256(f"{route_id}:{station_id}:{bucket}".encode()).hexdigest()
    return ((int(digest[:8], 16) % 10_000) / 10_000) * 2 - 1


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
        "live_drift": _live_drift(req.route_id, req.station_id),
    }


def predict_crowding(features: dict, capacity: int) -> tuple:
    """base occupancy x time-of-day peak x weekend/holiday damping x live
    drift — same heuristic shape as app/ml/model.py, with per-factor
    contributions and a confidence score reported alongside the point
    estimate. Swap this body for a real model call; build_feature_vector's
    output is already the feature dict a trained model would take."""
    factors: List[PredictionFactor] = []

    if features["hour"] in (8, 9, 18, 19):
        peak_multiplier = 1.3
        window = "morning" if features["hour"] < 12 else "evening"
        factors.append(PredictionFactor(
            name="rush_hour_peak", impact_pct=30.0,
            description=f"Hour {features['hour']}:00 falls in the {window} commute peak",
        ))
    else:
        peak_multiplier = 1.0
        factors.append(PredictionFactor(
            name="off_peak_hour", impact_pct=0.0,
            description="Outside the typical rush-hour windows (8-10, 18-20)",
        ))

    if features["is_weekend"] or features["is_holiday"]:
        calm_multiplier = 0.7
        reason = "holiday" if features["is_holiday"] else "weekend"
        factors.append(PredictionFactor(
            name="weekend_or_holiday_damping", impact_pct=-30.0,
            description=f"Ridership typically drops on a {reason}",
        ))
    else:
        calm_multiplier = 1.0

    drift = features["live_drift"]
    drift_pct = round(drift * 8, 1)  # +/-8% swing, matches DRIFT_BUCKET_SECONDS cadence
    factors.append(PredictionFactor(
        name="live_ridership_signal", impact_pct=drift_pct,
        description="Short-term variation from the live ticketing/sensor feed",
    ))

    predicted_ratio = features["occupancy_ratio"] * peak_multiplier * calm_multiplier * (1 + drift * 0.08)
    predicted_ratio = max(0.0, min(1.3, predicted_ratio))
    predicted_count = round(predicted_ratio * capacity)
    occupancy_pct = round(predicted_ratio * 100, 1)

    if occupancy_pct <= 40:
        level = CrowdingLevel.low
    elif occupancy_pct <= 75:
        level = CrowdingLevel.medium
    else:
        level = CrowdingLevel.high

    # Confidence dips near the LOW/MEDIUM/HIGH decision boundaries (40, 75)
    # where a small feature shift could flip the predicted class — same
    # idea as margin-based confidence for a real classifier.
    boundary_distance = min(abs(occupancy_pct - 40), abs(occupancy_pct - 75))
    confidence = round(min(0.98, 0.80 + boundary_distance / 200), 3)

    return predicted_count, occupancy_pct, level, confidence, factors


@router.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest) -> PredictionResponse:
    started = time.perf_counter()
    try:
        features = build_feature_vector(payload)
        predicted_count, occupancy_pct, level, confidence, factors = predict_crowding(
            features, payload.vehicle_capacity
        )
    except Exception as exc:  # model/feature-building failure, not a validation error
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")
    inference_time_ms = round((time.perf_counter() - started) * 1000, 2)

    return PredictionResponse(
        route_id=payload.route_id,
        station_id=payload.station_id,
        timestamp=payload.timestamp,
        predicted_passenger_count=predicted_count,
        predicted_occupancy_percentage=occupancy_pct,
        crowding_level=level,
        confidence=confidence,
        factors=factors,
        model_version=MODEL_VERSION,
        inference_time_ms=inference_time_ms,
    )
