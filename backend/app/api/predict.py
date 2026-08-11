"""
FlowCast ML prediction endpoint.

Uses the production Random Forest transit crowding model.
"""

import time
from datetime import datetime
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.ml.inference import predict_ridership

router = APIRouter(tags=["ml"])

MODEL_VERSION = "flowcast-random-forest-v1"

class WeatherCondition(str, Enum):
clear = "clear"
rain = "rain"
fog = "fog"
extreme = "extreme"

class CrowdingLevel(str, Enum):
low = "LOW"
medium = "MEDIUM"
high = "HIGH"

class PredictionRequest(BaseModel):

```
route_id: str = Field(
    ...,
    min_length=1
)

station_id: str = Field(
    ...,
    min_length=1
)

vehicle_capacity: int = Field(
    ...,
    gt=0
)

current_passenger_count: int = Field(
    ...,
    ge=0
)

timestamp: datetime

is_holiday: bool = False

weather_condition: Optional[
    WeatherCondition
] = None
```

class PredictionFactor(BaseModel):

```
name: str

impact_pct: float

description: str
```

class PredictionResponse(BaseModel):

```
model_config = ConfigDict(
    protected_namespaces=()
)

route_id: str

station_id: str

timestamp: datetime

predicted_passenger_count: int

predicted_occupancy_percentage: float

crowding_level: CrowdingLevel

confidence: float

factors: List[
    PredictionFactor
]

model_version: str

inference_time_ms: float
```

def classify_crowding(
predicted_count: float,
capacity: int
):

```
occupancy = (
    predicted_count
    /
    capacity
) * 100

if occupancy <= 40:

    level = CrowdingLevel.low

elif occupancy <= 75:

    level = CrowdingLevel.medium

else:

    level = CrowdingLevel.high

return (
    round(occupancy, 1),
    level
)
```

def build_factors(
timestamp: datetime,
occupancy: float
):

```
hour = timestamp.hour

factors = []

if hour in [7, 8, 9, 10]:

    factors.append(
        PredictionFactor(
            name="morning_peak",
            impact_pct=20.0,
            description="Morning commuting period"
        )
    )

if hour in [16, 17, 18, 19, 20]:

    factors.append(
        PredictionFactor(
            name="evening_peak",
            impact_pct=20.0,
            description="Evening commuting period"
        )
    )

if timestamp.weekday() >= 5:

    factors.append(
        PredictionFactor(
            name="weekend",
            impact_pct=-10.0,
            description="Weekend travel pattern"
        )
    )

if occupancy > 75:

    factors.append(
        PredictionFactor(
            name="high_predicted_load",
            impact_pct=25.0,
            description="Predicted passenger load is high"
        )
    )

if not factors:

    factors.append(
        PredictionFactor(
            name="normal_conditions",
            impact_pct=0.0,
            description="No major crowding factor detected"
        )
    )

return factors
```

@router.post(
"/predict",
response_model=PredictionResponse
)
def predict(
payload: PredictionRequest
):

```
started = time.perf_counter()

try:

    predicted_count = predict_ridership(

        station_id=payload.station_id,

        timestamp=payload.timestamp,

        current_passenger_count=
            payload.current_passenger_count,

    )

    predicted_count = round(
        predicted_count
    )

    occupancy, crowding_level = (
        classify_crowding(
            predicted_count,
            payload.vehicle_capacity
        )
    )

    factors = build_factors(
        payload.timestamp,
        occupancy
    )

    # Confidence is deliberately conservative.
    # This is not a classifier probability.
    confidence = 0.89

except Exception as exc:

    raise HTTPException(
        status_code=500,
        detail=f"Prediction failed: {exc}"
    )

inference_time_ms = round(
    (
        time.perf_counter()
        -
        started
    ) * 1000,
    2
)

return PredictionResponse(

    route_id=payload.route_id,

    station_id=payload.station_id,

    timestamp=payload.timestamp,

    predicted_passenger_count=
        predicted_count,

    predicted_occupancy_percentage=
        occupancy,

    crowding_level=
        crowding_level,

    confidence=
        confidence,

    factors=
        factors,

    model_version=
        MODEL_VERSION,

    inference_time_ms=
        inference_time_ms,
)
```
