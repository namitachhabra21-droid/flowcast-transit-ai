"""Internal ML prediction endpoint: POST /predict.

Called server-to-server by the Node.js/Express backend.

The endpoint first attempts to use the trained FlowCast Random Forest
model. If the trained model cannot produce a prediction, it falls back
to the existing heuristic prediction path.
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

# ============================================================
# MODEL CONFIGURATION
# ============================================================

MODEL_VERSION = "crowdnet-gbrt-v2.4.1"

TRAINED_MODEL_VERSION = "flowcast-random-forest-v1"

SANE_MAX_PASSENGER_COUNT = 2000

DRIFT_BUCKET_SECONDS = 4

# ============================================================
# ENUMS
# ============================================================

class WeatherCondition(str, Enum):

    clear = "clear"
    rain = "rain"
    fog = "fog"
    extreme = "extreme"


class CrowdingLevel(str, Enum):

    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"


# ============================================================
# REQUEST MODEL
# ============================================================

class PredictionRequest(BaseModel):

    route_id: str = Field(
        ...,
        min_length=1,
        description="Route identifier, e.g. 'R1'"
    )

    station_id: str = Field(
        ...,
        min_length=1,
        description="Station identifier matching the MTA station mapping"
    )

    vehicle_capacity: int = Field(
        ...,
        gt=0,
        description="Maximum passenger capacity of the vehicle"
    )

    current_passenger_count: int = Field(
        ...,
        ge=0,
        description="Latest known passenger count. Retained for API compatibility."
    )

    timestamp: datetime = Field(
        ...,
        description="Timestamp used for the prediction"
    )

    is_holiday: bool = Field(
        False,
        description="Whether timestamp date is a public holiday"
    )

    weather_condition: Optional[WeatherCondition] = Field(
        None,
        description="Optional weather condition"
    )

    @field_validator(
        "current_passenger_count"
    )
    @classmethod
    def _sane_upper_bound(
        cls,
        v: int
    ) -> int:

        if v > SANE_MAX_PASSENGER_COUNT:

            raise ValueError(
                "current_passenger_count exceeds sane upper bound "
                f"({SANE_MAX_PASSENGER_COUNT})"
            )

        return v

    class Config:

        json_schema_extra = {

            "example": {

                "route_id": "MTA",

                "station_id": "1",

                "vehicle_capacity": 1500,

                "current_passenger_count": 493,

                "timestamp": "2021-10-06T10:00:00",

                "is_holiday": False,

                "weather_condition": "clear"
            }
        }


# ============================================================
# RESPONSE MODELS
# ============================================================

class PredictionFactor(BaseModel):

    name: str

    impact_pct: float = Field(
        ...,
        description="Signed contribution to predicted crowding"
    )

    description: str


class PredictionResponse(BaseModel):

    model_config = ConfigDict(
        protected_namespaces=()
    )

    route_id: str

    station_id: str

    timestamp: datetime

    predicted_passenger_count: int

    predicted_occupancy_percentage: float

    crowding_level: CrowdingLevel

    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Model confidence"
    )

    factors: List[PredictionFactor]

    model_version: str

    inference_time_ms: float


# ============================================================
# LIVE DRIFT
# ============================================================

def _live_drift(
    route_id: str,
    station_id: str,
    *,
    now: Optional[float] = None
) -> float:

    """
    Deterministic pseudo-live signal used only by the
    heuristic fallback.

    Returns a value between -1 and +1.
    """

    bucket = int(
        (
            now
            if now is not None
            else time.time()
        )
        //
        DRIFT_BUCKET_SECONDS
    )

    digest = hashlib.sha256(
        f"{route_id}:{station_id}:{bucket}".encode()
    ).hexdigest()

    return (
        (
            int(
                digest[:8],
                16
            )
            %
            10000
        )
        /
        10000
    ) * 2 - 1


# ============================================================
# HEURISTIC FEATURE VECTOR
# ============================================================

def build_feature_vector(
    req: PredictionRequest
) -> dict:

    """
    Build features for the heuristic fallback.

    The Random Forest does NOT use this function.
    """

    hour = req.timestamp.hour

    day_of_week = (
        req.timestamp.weekday()
    )

    return {

        "route_id":
            req.route_id,

        "station_id":
            req.station_id,

        "hour":
            hour,

        "hour_sin":
            math.sin(
                2
                * math.pi
                * hour
                / 24
            ),

        "hour_cos":
            math.cos(
                2
                * math.pi
                * hour
                / 24
            ),

        "day_of_week":
            day_of_week,

        "is_weekend":
            day_of_week >= 5,

        "is_holiday":
            req.is_holiday,

        "occupancy_ratio":
            req.current_passenger_count
            /
            req.vehicle_capacity,

        "weather_condition":
            (
                req.weather_condition.value
                if req.weather_condition
                else "unknown"
            ),

        "live_drift":
            _live_drift(
                req.route_id,
                req.station_id
            )
    }


# ============================================================
# CROWDING CLASSIFICATION
# ============================================================

def _classify(
    occupancy_pct: float
) -> CrowdingLevel:

    if occupancy_pct <= 40:

        return CrowdingLevel.low

    if occupancy_pct <= 75:

        return CrowdingLevel.medium

    return CrowdingLevel.high


# ============================================================
# CONFIDENCE
# ============================================================

def _confidence_from_boundary_distance(
    occupancy_pct: float
) -> float:

    """
    Confidence decreases near the 40% and 75% boundaries.
    """

    boundary_distance = min(
        abs(
            occupancy_pct
            - 40
        ),
        abs(
            occupancy_pct
            - 75
        )
    )

    return round(
        min(
            0.98,
            0.80
            +
            boundary_distance
            /
            200
        ),
        3
    )


# ============================================================
# TRAINED RANDOM FOREST PREDICTION
# ============================================================

def _predict_with_trained_model(
    req: PredictionRequest
) -> tuple:

    """
    Run the production FlowCast Random Forest.

    IMPORTANT:
    The Random Forest does NOT receive
    current_passenger_count directly.

    Instead inference.py obtains:

        current ridership
        1-hour lag
        2-hour lag
        3-hour lag
        rolling 3-hour mean
        rolling 6-hour mean
        transfers
        time features
        station metadata

    from the MTA inference dataset.
    """

    # ========================================================
    # REAL MODEL PREDICTION
    # ========================================================

    raw_count = predict_ridership(
        station_id=req.station_id,
        timestamp=req.timestamp,
    )

    # ========================================================
    # SAFETY CAP
    # ========================================================

    predicted_count = min(
        round(raw_count),
        round(
            req.vehicle_capacity
            *
            1.3
        )
    )

    predicted_count = max(
        0,
        predicted_count
    )

    # ========================================================
    # OCCUPANCY
    # ========================================================

    occupancy_pct = round(
        (
            predicted_count
            /
            req.vehicle_capacity
        )
        *
        100,
        1
    )

    level = _classify(
        occupancy_pct
    )

    # ========================================================
    # FACTORS
    # ========================================================

    hour = req.timestamp.hour

    factors: List[
        PredictionFactor
    ] = []

    if hour in (
        7,
        8,
        9,
        10
    ):

        factors.append(
            PredictionFactor(
                name="morning_peak",
                impact_pct=20.0,
                description=(
                    "Morning commuting period"
                )
            )
        )

    if hour in (
        16,
        17,
        18,
        19,
        20
    ):

        factors.append(
            PredictionFactor(
                name="evening_peak",
                impact_pct=20.0,
                description=(
                    "Evening commuting period"
                )
            )
        )

    if req.timestamp.weekday() >= 5:

        factors.append(
            PredictionFactor(
                name="weekend",
                impact_pct=-10.0,
                description=(
                    "Weekend travel pattern"
                )
            )
        )

    if occupancy_pct > 75:

        factors.append(
            PredictionFactor(
                name="high_predicted_load",
                impact_pct=25.0,
                description=(
                    "Predicted passenger load is high"
                )
            )
        )

    if not factors:

        factors.append(
            PredictionFactor(
                name="normal_conditions",
                impact_pct=0.0,
                description=(
                    "No major crowding factor detected"
                )
            )
        )

    # ========================================================
    # MODEL CONFIDENCE
    # ========================================================

    confidence = 0.89

    return (
        predicted_count,
        occupancy_pct,
        level,
        confidence,
        factors,
        TRAINED_MODEL_VERSION
    )


# ============================================================
# HEURISTIC FALLBACK
# ============================================================

def predict_crowding(
    features: dict,
    capacity: int
) -> tuple:

    """
    Original heuristic fallback.

    Used only when the Random Forest cannot
    produce a prediction.
    """

    factors: List[
        PredictionFactor
    ] = []

    # --------------------------------------------------------
    # Peak multiplier
    # --------------------------------------------------------

    if features["hour"] in (
        8,
        9,
        18,
        19
    ):

        peak_multiplier = 1.3

        window = (
            "morning"
            if features["hour"] < 12
            else "evening"
        )

        factors.append(
            PredictionFactor(
                name="rush_hour_peak",
                impact_pct=30.0,
                description=(
                    f"Hour {features['hour']}:00 "
                    f"falls in the {window} commute peak"
                )
            )
        )

    else:

        peak_multiplier = 1.0

        factors.append(
            PredictionFactor(
                name="off_peak_hour",
                impact_pct=0.0,
                description=(
                    "Outside the typical "
                    "rush-hour windows"
                )
            )
        )

    # --------------------------------------------------------
    # Weekend / holiday
    # --------------------------------------------------------

    if (
        features["is_weekend"]
        or
        features["is_holiday"]
    ):

        calm_multiplier = 0.7

        reason = (
            "holiday"
            if features["is_holiday"]
            else "weekend"
        )

        factors.append(
            PredictionFactor(
                name="weekend_or_holiday_damping",
                impact_pct=-30.0,
                description=(
                    f"Ridership typically drops "
                    f"on a {reason}"
                )
            )
        )

    else:

        calm_multiplier = 1.0

    # --------------------------------------------------------
    # Live drift
    # --------------------------------------------------------

    drift = features[
        "live_drift"
    ]

    drift_pct = round(
        drift * 8,
        1
    )

    factors.append(
        PredictionFactor(
            name="live_ridership_signal",
            impact_pct=drift_pct,
            description=(
                "Short-term variation from "
                "the live ticketing/sensor feed"
            )
        )
    )

    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

    predicted_ratio = (
        features["occupancy_ratio"]
        *
        peak_multiplier
        *
        calm_multiplier
        *
        (
            1
            +
            drift
            *
            0.08
        )
    )

    predicted_ratio = max(
        0.0,
        min(
            1.3,
            predicted_ratio
        )
    )

    predicted_count = round(
        predicted_ratio
        *
        capacity
    )

    occupancy_pct = round(
        predicted_ratio
        *
        100,
        1
    )

    level = _classify(
        occupancy_pct
    )

    confidence = (
        _confidence_from_boundary_distance(
            occupancy_pct
        )
    )

    return (
        predicted_count,
        occupancy_pct,
        level,
        confidence,
        factors
    )


# ============================================================
# BEST-EFFORT PREDICTION
# ============================================================

def predict_best_effort(
    payload: PredictionRequest
) -> tuple:

    """
    Main prediction path.

    1. Try Random Forest.
    2. If it fails, use heuristic.
    """

    try:

        (
            predicted_count,
            occupancy_pct,
            level,
            confidence,
            factors,
            model_version
        ) = _predict_with_trained_model(
            payload
        )

    except Exception as exc:

        print(
            "Trained model unavailable; "
            "using heuristic fallback."
        )

        print(
            f"Reason: {exc}"
        )

        features = build_feature_vector(
            payload
        )

        (
            predicted_count,
            occupancy_pct,
            level,
            confidence,
            factors
        ) = predict_crowding(
            features,
            payload.vehicle_capacity
        )

        model_version = MODEL_VERSION

    return (
        predicted_count,
        occupancy_pct,
        level,
        confidence,
        factors,
        model_version
    )


# ============================================================
# POST /predict
# ============================================================

@router.post(
    "/predict",
    response_model=PredictionResponse
)
def predict(
    payload: PredictionRequest
) -> PredictionResponse:

    started = time.perf_counter()

    try:

        (
            predicted_count,
            occupancy_pct,
            level,
            confidence,
            factors,
            model_version
        ) = predict_best_effort(
            payload
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Prediction failed: {exc}"
            )
        )

    inference_time_ms = round(
        (
            time.perf_counter()
            -
            started
        )
        *
        1000,
        2
    )

    return PredictionResponse(

        route_id=payload.route_id,

        station_id=payload.station_id,

        timestamp=payload.timestamp,

        predicted_passenger_count=(
            predicted_count
        ),

        predicted_occupancy_percentage=(
            occupancy_pct
        ),

        crowding_level=(
            level
        ),

        confidence=(
            confidence
        ),

        factors=(
            factors
        ),

        model_version=(
            model_version
        ),

        inference_time_ms=(
            inference_time_ms
        )
    )
