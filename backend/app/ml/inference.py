# -*- coding: utf-8 -*-

"""
FlowCast Transit AI
Production Random Forest Inference

Uses:
    - Production Random Forest
    - Station mapping
    - Station metadata
    - Historical MTA inference data

Prediction:
    Next-hour station ridership
"""

import os
import math
import joblib
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

ARTIFACT_DIR = os.path.join(
    BASE_DIR,
    "artifacts"
)

DATA_PATH = os.path.join(
    BASE_DIR,
    "..",
    "data",
    "flowcast_mta_data.csv"
)

MODEL_PATH = os.path.join(
    ARTIFACT_DIR,
    "transit_crowding_model.joblib"
)

FEATURE_PATH = os.path.join(
    ARTIFACT_DIR,
    "feature_columns.joblib"
)

MAPPING_PATH = os.path.join(
    ARTIFACT_DIR,
    "station_mapping.joblib"
)

METADATA_PATH = os.path.join(
    ARTIFACT_DIR,
    "station_metadata.csv"
)


# ============================================================
# LOAD MODEL
# ============================================================

print("Loading FlowCast Random Forest...")

MODEL = joblib.load(
    MODEL_PATH
)

FEATURE_COLUMNS = joblib.load(
    FEATURE_PATH
)

STATION_MAPPING = joblib.load(
    MAPPING_PATH
)

STATION_METADATA = pd.read_csv(
    METADATA_PATH,
    low_memory=False
)


# ============================================================
# LOAD MTA DATA
# ============================================================

print("Loading MTA inference data...")

MTA_DATA = pd.read_csv(
    DATA_PATH,
    low_memory=False
)

MTA_DATA["datetime"] = pd.to_datetime(
    MTA_DATA["datetime"],
    errors="coerce"
)

MTA_DATA["station_complex_id"] = (
    MTA_DATA["station_complex_id"]
    .astype(str)
    .str.strip()
)

MTA_DATA = MTA_DATA.sort_values(
    [
        "station_complex_id",
        "datetime"
    ]
).reset_index(
    drop=True
)


# ============================================================
# FAST TIMESTAMP LOOKUP
# ============================================================

MTA_LOOKUP = (
    MTA_DATA
    .set_index(
        [
            "station_complex_id",
            "datetime"
        ]
    )
    .sort_index()
)


# ============================================================
# GET STATION METADATA
# ============================================================

def get_station_metadata(
    station_id: str
):

    station_id = str(
        station_id
    )

    rows = STATION_METADATA[
        STATION_METADATA[
            "station_complex_id"
        ].astype(str)
        == station_id
    ]

    if rows.empty:

        raise ValueError(
            f"Station '{station_id}' "
            f"not found in station metadata."
        )

    return rows.iloc[0]


# ============================================================
# GET RIDERSHIP AT EXACT TIMESTAMP
# ============================================================

def get_ridership(
    station_id: str,
    timestamp
):

    station_id = str(
        station_id
    )

    timestamp = pd.Timestamp(
        timestamp
    )

    try:

        row = MTA_LOOKUP.loc[
            (
                station_id,
                timestamp
            )
        ]

        if isinstance(
            row,
            pd.DataFrame
        ):

            row = row.iloc[0]

        return float(
            row["ridership"]
        )

    except KeyError:

        return None


# ============================================================
# GET TRANSFERS AT EXACT TIMESTAMP
# ============================================================

def get_transfers(
    station_id: str,
    timestamp
):

    station_id = str(
        station_id
    )

    timestamp = pd.Timestamp(
        timestamp
    )

    try:

        row = MTA_LOOKUP.loc[
            (
                station_id,
                timestamp
            )
        ]

        if isinstance(
            row,
            pd.DataFrame
        ):

            row = row.iloc[0]

        return float(
            row["transfers"]
        )

    except KeyError:

        return None


# ============================================================
# BUILD FEATURES
# ============================================================

def build_features(
    station_id: str,
    timestamp
):

    station_id = str(
        station_id
    )

    timestamp = pd.Timestamp(
        timestamp
    )

    # --------------------------------------------------------
    # Station validation
    # --------------------------------------------------------

    if station_id not in STATION_MAPPING:

        raise ValueError(
            f"Station '{station_id}' "
            f"not found in station mapping."
        )

    station_numeric = int(
        STATION_MAPPING[
            station_id
        ]
    )

    # --------------------------------------------------------
    # Current observation
    # --------------------------------------------------------

    current_ridership = get_ridership(
        station_id,
        timestamp
    )

    if current_ridership is None:

        raise ValueError(
            f"No MTA observation exists for "
            f"station {station_id} at "
            f"{timestamp}."
        )

    # --------------------------------------------------------
    # Historical lags
    # --------------------------------------------------------

    lag_1h = get_ridership(
        station_id,
        timestamp -
        pd.Timedelta(hours=1)
    )

    lag_2h = get_ridership(
        station_id,
        timestamp -
        pd.Timedelta(hours=2)
    )

    lag_3h = get_ridership(
        station_id,
        timestamp -
        pd.Timedelta(hours=3)
    )

    if any(
        pd.isna(x)
        for x in [
            lag_1h,
            lag_2h,
            lag_3h
        ]
    ):

        raise ValueError(
            "Insufficient historical observations "
            "for 1h/2h/3h lag features."
        )

    # --------------------------------------------------------
    # Rolling 3h
    # --------------------------------------------------------

    rolling_mean_3h = float(
        np.mean(
            [
                lag_1h,
                lag_2h,
                lag_3h
            ]
        )
    )

    # --------------------------------------------------------
    # Rolling 6h
    # --------------------------------------------------------

    six_hour_values = []

    for hours_back in range(
        1,
        7
    ):

        value = get_ridership(
            station_id,
            timestamp -
            pd.Timedelta(
                hours=hours_back
            )
        )

        if value is not None:

            six_hour_values.append(
                value
            )

    if len(
        six_hour_values
    ) < 6:

        raise ValueError(
            "Insufficient historical observations "
            "for 6-hour rolling feature."
        )

    rolling_mean_6h = float(
        np.mean(
            six_hour_values
        )
    )

    # --------------------------------------------------------
    # Transfers
    # --------------------------------------------------------

    transfers = get_transfers(
        station_id,
        timestamp
    )

    if transfers is None:

        transfers = 0.0

    # --------------------------------------------------------
    # Time features
    # --------------------------------------------------------

    hour = timestamp.hour

    day_of_week = (
        timestamp.dayofweek
    )

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
        is_morning_peak
        or
        is_evening_peak
    )

    hour_sin = math.sin(
        2 *
        math.pi *
        hour /
        24
    )

    hour_cos = math.cos(
        2 *
        math.pi *
        hour /
        24
    )

    day_sin = math.sin(
        2 *
        math.pi *
        day_of_week /
        7
    )

    day_cos = math.cos(
        2 *
        math.pi *
        day_of_week /
        7
    )

    # --------------------------------------------------------
    # Station information
    # --------------------------------------------------------

    station_info = get_station_metadata(
        station_id
    )

    latitude = float(
        station_info["latitude"]
    )

    longitude = float(
        station_info["longitude"]
    )

    # --------------------------------------------------------
    # EXACT TRAINING FEATURES
    # --------------------------------------------------------

    features = {

        "ridership":
            current_ridership,

        "ridership_lag_1h":
            lag_1h,

        "ridership_lag_2h":
            lag_2h,

        "ridership_lag_3h":
            lag_3h,

        "rolling_mean_3h":
            rolling_mean_3h,

        "rolling_mean_6h":
            rolling_mean_6h,

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
            transfers,

        "station_id_numeric":
            station_numeric
    }

    # --------------------------------------------------------
    # Preserve exact feature order
    # --------------------------------------------------------

    X = pd.DataFrame(
        [[
            features[column]
            for column in FEATURE_COLUMNS
        ]],
        columns=FEATURE_COLUMNS
    )

    return X


# ============================================================
# PREDICT
# ============================================================

def predict_ridership(
    station_id: str,
    timestamp
):

    X = build_features(
        station_id,
        timestamp
    )

    prediction = MODEL.predict(
        X
    )[0]

    prediction = max(
        0,
        float(prediction)
    )

    return prediction
