import os
import math
import joblib
import pandas as pd
import numpy as np

# ============================================================

# PATHS

# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(**file**))

ARTIFACT_DIR = os.path.join(
BASE_DIR,
"artifacts"
)

MODEL_PATH = os.path.join(
ARTIFACT_DIR,
"transit_crowding_model.joblib"
)

FEATURE_PATH = os.path.join(
ARTIFACT_DIR,
"feature_columns.joblib"
)

STATION_MAPPING_PATH = os.path.join(
ARTIFACT_DIR,
"station_mapping.joblib"
)

STATION_METADATA_PATH = os.path.join(
ARTIFACT_DIR,
"station_metadata.csv"
)

# ============================================================

# LOAD MODEL ARTIFACTS ONCE

# ============================================================

print("Loading FlowCast ML model...")

MODEL = joblib.load(MODEL_PATH)

FEATURE_COLUMNS = joblib.load(
FEATURE_PATH
)

STATION_MAPPING = joblib.load(
STATION_MAPPING_PATH
)

STATION_METADATA = pd.read_csv(
STATION_METADATA_PATH
)

print("ML model loaded successfully.")
print("Features:", len(FEATURE_COLUMNS))
print("Stations:", len(STATION_MAPPING))

# ============================================================

# FEATURE ENGINEERING

# ============================================================

def build_features(
station_id: str,
timestamp,
current_passenger_count: int,
lag_1h: float | None = None,
lag_2h: float | None = None,
lag_3h: float | None = None,
rolling_mean_3h: float | None = None,
rolling_mean_6h: float | None = None,
transfers: float | None = None,
):
"""
Build the exact 20 features used during production training.
"""

```
timestamp = pd.Timestamp(timestamp)

hour = timestamp.hour

day_of_week = timestamp.dayofweek

is_weekend = int(
    day_of_week >= 5
)

is_morning_peak = int(
    hour in [7, 8, 9, 10]
)

is_evening_peak = int(
    hour in [16, 17, 18, 19, 20]
)

is_peak_hour = int(
    is_morning_peak or is_evening_peak
)

hour_sin = math.sin(
    2 * math.pi * hour / 24
)

hour_cos = math.cos(
    2 * math.pi * hour / 24
)

day_sin = math.sin(
    2 * math.pi * day_of_week / 7
)

day_cos = math.cos(
    2 * math.pi * day_of_week / 7
)

# --------------------------------------------------------
# Station lookup
# --------------------------------------------------------

station_key = str(
    station_id
)

station_numeric = None

# Handle mappings saved in different formats
if isinstance(STATION_MAPPING, dict):

    if station_key in STATION_MAPPING:
        station_numeric = STATION_MAPPING[station_key]

    elif station_id in STATION_MAPPING:
        station_numeric = STATION_MAPPING[station_id]

if station_numeric is None:

    raise ValueError(
        f"Station '{station_id}' was not found "
        f"in the production station mapping."
    )

# --------------------------------------------------------
# Station metadata
# --------------------------------------------------------

station_row = STATION_METADATA[
    STATION_METADATA[
        "station_complex_id"
    ].astype(str)
    == station_key
]

if station_row.empty:

    raise ValueError(
        f"Station metadata not found for '{station_id}'."
    )

station_row = station_row.iloc[0]

latitude = float(
    station_row["latitude"]
)

longitude = float(
    station_row["longitude"]
)

# --------------------------------------------------------
# Fallback values
#
# These are temporary fallbacks for the first integration.
# We will replace them with actual historical/live values.
# --------------------------------------------------------

if lag_1h is None:
    lag_1h = current_passenger_count

if lag_2h is None:
    lag_2h = lag_1h

if lag_3h is None:
    lag_3h = lag_2h

if rolling_mean_3h is None:

    rolling_mean_3h = np.mean(
        [
            lag_1h,
            lag_2h,
            lag_3h
        ]
    )

if rolling_mean_6h is None:

    rolling_mean_6h = rolling_mean_3h

if transfers is None:

    transfers = 0.0

# --------------------------------------------------------
# EXACT MODEL FEATURES
# --------------------------------------------------------

features = {

    "ridership":
        float(current_passenger_count),

    "ridership_lag_1h":
        float(lag_1h),

    "ridership_lag_2h":
        float(lag_2h),

    "ridership_lag_3h":
        float(lag_3h),

    "rolling_mean_3h":
        float(rolling_mean_3h),

    "rolling_mean_6h":
        float(rolling_mean_6h),

    "hour":
        hour,

    "day_of_week":
        day_of_week,

    "is_weekend":
        is_weekend,

    "is_morning_peak":
        is_morning_peak,

    "is_evening_peak":
        is_evening_peak,

    "is_peak_hour":
        is_peak_hour,

    "hour_sin":
        hour_sin,

    "hour_cos":
        hour_cos,

    "day_sin":
        day_sin,

    "day_cos":
        day_cos,

    "latitude":
        latitude,

    "longitude":
        longitude,

    "transfers":
        float(transfers),

    "station_id_numeric":
        station_numeric
}

# Make absolutely sure feature order is identical
# to training.

X = pd.DataFrame(
    [[
        features[column]
        for column in FEATURE_COLUMNS
    ]],
    columns=FEATURE_COLUMNS
)

return X
```

# ============================================================

# PREDICTION

# ============================================================

def predict_ridership(
station_id: str,
timestamp,
current_passenger_count: int,
lag_1h: float | None = None,
lag_2h: float | None = None,
lag_3h: float | None = None,
rolling_mean_3h: float | None = None,
rolling_mean_6h: float | None = None,
transfers: float | None = None,
):

```
X = build_features(
    station_id=station_id,
    timestamp=timestamp,
    current_passenger_count=current_passenger_count,
    lag_1h=lag_1h,
    lag_2h=lag_2h,
    lag_3h=lag_3h,
    rolling_mean_3h=rolling_mean_3h,
    rolling_mean_6h=rolling_mean_6h,
    transfers=transfers,
)

prediction = MODEL.predict(
    X
)[0]

prediction = max(
    0,
    float(prediction)
)

return prediction
```
