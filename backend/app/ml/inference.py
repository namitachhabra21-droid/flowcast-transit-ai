"""Trained-model inference for /predict.

Loads a Random Forest ridership model + its companion artifacts
(feature columns, station mapping, station metadata) once at import time.

Loading is defensive on purpose: the artifacts currently checked in are a
partial upload (missing `transit_crowding_model.joblib`, and the station
mapping/metadata are keyed by an NYC subway complex-ID scheme that has no
overlap with this app's Delhi Metro station IDs). Rather than crash the
whole FastAPI app on import if any artifact is missing or mismatched,
loading failures are caught here and predict_ridership() raises a plain
RuntimeError/ValueError at call time instead — app/api/predict.py catches
that and falls back to the heuristic model.
"""
import math
import os
from typing import Optional

import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACT_DIR = os.path.join(BASE_DIR, "artifacts")

MODEL_PATH = os.path.join(ARTIFACT_DIR, "transit_crowding_model.joblib")
FEATURE_PATH = os.path.join(ARTIFACT_DIR, "feature_columns.joblib")
STATION_MAPPING_PATH = os.path.join(ARTIFACT_DIR, "station_mapping.joblib")
STATION_METADATA_PATH = os.path.join(ARTIFACT_DIR, "station_metadata.csv")


def _load_artifacts():
    try:
        model = joblib.load(MODEL_PATH)
        feature_columns = joblib.load(FEATURE_PATH)
        station_mapping = joblib.load(STATION_MAPPING_PATH)
        station_metadata = pd.read_csv(STATION_METADATA_PATH)
    except FileNotFoundError as exc:
        print(f"[app.ml.inference] trained model artifacts unavailable, /predict will use the heuristic fallback: {exc}")
        return None, None, None, None
    print(f"[app.ml.inference] loaded trained model — {len(feature_columns)} features, {len(station_mapping)} stations")
    return model, feature_columns, station_mapping, station_metadata


MODEL, FEATURE_COLUMNS, STATION_MAPPING, STATION_METADATA = _load_artifacts()


def build_features(
    station_id: str,
    timestamp,
    current_passenger_count: int,
    lag_1h: Optional[float] = None,
    lag_2h: Optional[float] = None,
    lag_3h: Optional[float] = None,
    rolling_mean_3h: Optional[float] = None,
    rolling_mean_6h: Optional[float] = None,
    transfers: Optional[float] = None,
) -> pd.DataFrame:
    """Build the exact feature row the trained model expects."""
    timestamp = pd.Timestamp(timestamp)
    hour = timestamp.hour
    day_of_week = timestamp.dayofweek
    is_weekend = int(day_of_week >= 5)
    is_morning_peak = int(hour in [7, 8, 9, 10])
    is_evening_peak = int(hour in [16, 17, 18, 19, 20])
    is_peak_hour = int(is_morning_peak or is_evening_peak)
    hour_sin = math.sin(2 * math.pi * hour / 24)
    hour_cos = math.cos(2 * math.pi * hour / 24)
    day_sin = math.sin(2 * math.pi * day_of_week / 7)
    day_cos = math.cos(2 * math.pi * day_of_week / 7)

    station_key = str(station_id)
    station_numeric = STATION_MAPPING.get(station_key, STATION_MAPPING.get(station_id))
    if station_numeric is None:
        raise ValueError(f"Station '{station_id}' was not found in the production station mapping.")

    station_row = STATION_METADATA[STATION_METADATA["station_complex_id"].astype(str) == station_key]
    if station_row.empty:
        raise ValueError(f"Station metadata not found for '{station_id}'.")
    station_row = station_row.iloc[0]
    latitude = float(station_row["latitude"])
    longitude = float(station_row["longitude"])

    # Fallbacks for the first integration — replace with real historical/live values later.
    if lag_1h is None:
        lag_1h = current_passenger_count
    if lag_2h is None:
        lag_2h = lag_1h
    if lag_3h is None:
        lag_3h = lag_2h
    if rolling_mean_3h is None:
        rolling_mean_3h = float(np.mean([lag_1h, lag_2h, lag_3h]))
    if rolling_mean_6h is None:
        rolling_mean_6h = rolling_mean_3h
    if transfers is None:
        transfers = 0.0

    features = {
        "ridership": float(current_passenger_count),
        "ridership_lag_1h": float(lag_1h),
        "ridership_lag_2h": float(lag_2h),
        "ridership_lag_3h": float(lag_3h),
        "rolling_mean_3h": float(rolling_mean_3h),
        "rolling_mean_6h": float(rolling_mean_6h),
        "hour": hour,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "is_morning_peak": is_morning_peak,
        "is_evening_peak": is_evening_peak,
        "is_peak_hour": is_peak_hour,
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
        "day_sin": day_sin,
        "day_cos": day_cos,
        "latitude": latitude,
        "longitude": longitude,
        "transfers": float(transfers),
        "station_id_numeric": station_numeric,
    }
    return pd.DataFrame([[features[column] for column in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)


def predict_ridership(
    station_id: str,
    timestamp,
    current_passenger_count: int,
    lag_1h: Optional[float] = None,
    lag_2h: Optional[float] = None,
    lag_3h: Optional[float] = None,
    rolling_mean_3h: Optional[float] = None,
    rolling_mean_6h: Optional[float] = None,
    transfers: Optional[float] = None,
) -> float:
    if MODEL is None:
        raise RuntimeError("trained model artifacts are not available")
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
    prediction = MODEL.predict(X)[0]
    return max(0.0, float(prediction))
