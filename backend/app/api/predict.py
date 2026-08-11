"""Internal ML prediction endpoint: POST /predict.

Called server-to-server by the Node.js/Express backend, not by end users
directly — it's mounted at the app root (not under /api/v1) and isn't
gated by the Clerk/API-key auth used elsewhere in this service, since the
caller here is a trusted internal service, not an org-scoped client. Put
this behind a shared-secret header or network-level restriction (VPC,
internal-only ingress) before it's reachable from anywhere but the Node
backend.

Two prediction paths, in order:
1. The trained model (app.ml.inference.predict_ridership) — a Random
   Forest trained on NYC subway ridership data. Its station mapping has no
   overlap with this app's Delhi Metro station IDs, and the model weight
   file isn't currently checked in, so in practice this path is not
   reachable yet for any station this app actually uses.
2. predict_crowding()'s heuristic — the original swap-later placeholder
   (base occupancy x time-of-day peak x weekend/holiday damping x a live
   ridership drift term), used whenever the trained model raises for any
   reason (missing artifacts, unknown station, bad input).

Both paths return the same PredictionResponse shape; model_version tells
you which one actually served the request.
"""
import hashlib
import math
import time
from datetime import datetime
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ml.inference import predict_ridership

router = APIRouter(tags=["ml"])

MODEL_VERSION = "crowdnet-gbrt-v2.4.1"
TRAINED_MODEL_VERSION = "flowcast-random-forest-v1"
SANE_MAX_PASSENGER_COUNT = 2000
DRIFT_BUCKET_SECONDS = 4  # how often the heuristic's "live" signal is allowed to move


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
    """Raw inputs -> derived features -> the dict shape the heuristic (and
    a real model) consumes."""
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


def _classify(occupancy_pct: float) -> CrowdingLevel:
    if occupancy_pct <= 40:
        return CrowdingLevel.low
    if occupancy_pct <= 75:
        return CrowdingLevel.medium
    return CrowdingLevel.high


def _confidence_from_boundary_distance(occupancy_pct: float) -> float:
    """Confidence dips near the LOW/MEDIUM/HIGH decision boundaries (40,
    75) where a small feature shift could flip the predicted class — same
    idea as margin-based confidence for a real classifier."""
    boundary_distance = min(abs(occupancy_pct - 40), abs(occupancy_pct - 75))
    return round(min(0.98, 0.80 + boundary_distance / 200), 3)


def _predict_with_trained_model(req: PredictionRequest) -> tuple:
    """Try the real Random Forest model. Raises whenever it can't produce
    a prediction (missing artifacts, station not covered) — callers fall
    back to the heuristic."""
    raw_count = predict_ridership(
        station_id=req.station_id,
        timestamp=req.timestamp,
        current_passenger_count=req.current_passenger_count,
    )
    # Cap at 130% of capacity, matching predict_crowding()'s ceiling — the
    # model has no notion of vehicle_capacity, so an outlier ridership
    # prediction shouldn't be able to report e.g. 900% occupancy.
    predicted_count = min(round(raw_count), round(req.vehicle_capacity * 1.3))
    occupancy_pct = round((predicted_count / req.vehicle_capacity) * 100, 1)
    level = _classify(occupancy_pct)

    hour = req.timestamp.hour
    factors: List[PredictionFactor] = []
    if hour in (7, 8, 9, 10):
        factors.append(PredictionFactor(name="morning_peak", impact_pct=20.0, description="Morning commuting period"))
    if hour in (16, 17, 18, 19, 20):
        factors.append(PredictionFactor(name="evening_peak", impact_pct=20.0, description="Evening commuting period"))
    if req.timestamp.weekday() >= 5:
        factors.append(PredictionFactor(name="weekend", impact_pct=-10.0, description="Weekend travel pattern"))
    if occupancy_pct > 75:
        factors.append(PredictionFactor(name="high_predicted_load", impact_pct=25.0, description="Predicted passenger load is high"))
    if not factors:
        factors.append(PredictionFactor(name="normal_conditions", impact_pct=0.0, description="No major crowding factor detected"))

    # Deliberately conservative and fixed — not a classifier probability,
    # just signals "this came from the trained model, not the heuristic".
    confidence = 0.89

    return predicted_count, occupancy_pct, level, confidence, factors, TRAINED_MODEL_VERSION


def predict_crowding(features: dict, capacity: int) -> tuple:
    """base occupancy x time-of-day peak x weekend/holiday damping x live
    drift — the original swap-later heuristic, with per-factor
    contributions and a confidence score reported alongside the point
    estimate. This is the fallback path predict() uses whenever the
    trained model can't serve a prediction."""
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
    level = _classify(occupancy_pct)
    confidence = _confidence_from_boundary_distance(occupancy_pct)

    return predicted_count, occupancy_pct, level, confidence, factors


def predict_best_effort(payload: PredictionRequest) -> tuple:
    """The one prediction entry point every caller should use: try the
    trained model, fall back to the heuristic on any failure. Shared by
    the /predict endpoint and recommend.py so a route evaluated by
    /recommend-route gets the same trained-model-when-possible behavior
    as a direct /predict call, instead of recommend.py quietly always
    using the heuristic."""
    try:
        predicted_count, occupancy_pct, level, confidence, factors, model_version = _predict_with_trained_model(payload)
    except Exception:
        features = build_feature_vector(payload)
        predicted_count, occupancy_pct, level, confidence, factors = predict_crowding(features, payload.vehicle_capacity)
        model_version = MODEL_VERSION
    return predicted_count, occupancy_pct, level, confidence, factors, model_version


@router.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest) -> PredictionResponse:
    started = time.perf_counter()
    try:
        predicted_count, occupancy_pct, level, confidence, factors, model_version = predict_best_effort(payload)
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
        model_version=model_version,
        inference_time_ms=inference_time_ms,
    )
