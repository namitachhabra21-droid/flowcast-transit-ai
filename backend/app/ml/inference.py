# -*- coding: utf-8 -*-

"""
FlowCast Transit AI — trained-model inference for /predict.

Uses:
    - Production Random Forest (transit_crowding_model.joblib, pruned to
      20 trees so it fits Render's free-tier 512MB RAM — see the comment
      near MODEL_PATH below)
    - Station mapping / station metadata (extended with this app's 9 Delhi
      Metro stations and their real public lat/long — see station_mapping
      .joblib / station_metadata.csv)
    - Historical MTA ridership data (flowcast_mta_data.csv), used as a
      source of real lag/rolling features when available

Prediction: next-hour station ridership.

Data reality check: flowcast_mta_data.csv is sparse, not continuous
hourly data — e.g. one NYC station has only 315 readings spread across a
full year, with gaps of days at a time between them. Real-world requests
from this app always ask for "right now" (2026), which never has an exact
match in a 2021-2022 dataset, and the 9 Delhi stations have no rows in it
at all (it's NYC-only). Requiring an *exact* hour-by-hour match for every
lag feature — the original version of this file — meant the trained
model could never actually run for any request this app makes; it always
raised and silently fell back to the heuristic.

Fixed here by making the historical lookups nearest-neighbor instead of
exact-match (_nearest_reading): use the closest real reading to the
target time when one exists within a reasonable window, otherwise fall
back to the caller-supplied current_passenger_count. This keeps the
"prefer real historical data" intent while guaranteeing predict_ridership
can actually produce a prediction instead of only existing in theory.
"""

import math
import os

import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACT_DIR = os.path.join(BASE_DIR, "artifacts")

DATA_PATH = os.path.join(BASE_DIR, "..", "data", "flowcast_mta_data.csv")
MODEL_PATH = os.path.join(ARTIFACT_DIR, "transit_crowding_model.joblib")
FEATURE_PATH = os.path.join(ARTIFACT_DIR, "feature_columns.joblib")
MAPPING_PATH = os.path.join(ARTIFACT_DIR, "station_mapping.joblib")
METADATA_PATH = os.path.join(ARTIFACT_DIR, "station_metadata.csv")

# How far the nearest historical reading is allowed to be from the
# requested time before we stop trusting it as a stand-in and fall back
# to current_passenger_count instead.
MAX_READING_DISTANCE = pd.Timedelta(days=45)


def _load_artifacts():
    """Defensive on purpose: a missing/corrupt artifact (model, mapping,
    metadata, or the MTA dataset) must not crash the whole FastAPI app at
    import time. predict_ridership() raises a plain RuntimeError/ValueError
    at call time instead — app/api/predict.py catches that and falls back
    to the heuristic model."""
    try:
        model = joblib.load(MODEL_PATH)
        feature_columns = joblib.load(FEATURE_PATH)
        station_mapping = joblib.load(MAPPING_PATH)
        station_metadata = pd.read_csv(METADATA_PATH, low_memory=False)
    except Exception as exc:
        print(f"[app.ml.inference] trained model artifacts unavailable, /predict will use the heuristic fallback: {exc}")
        return None, None, None, None, {}

    try:
        mta_data = pd.read_csv(DATA_PATH, low_memory=False)
        mta_data["datetime"] = pd.to_datetime(mta_data["datetime"], errors="coerce")
        mta_data["station_complex_id"] = mta_data["station_complex_id"].astype(str).str.strip()
        mta_data = mta_data.dropna(subset=["datetime"]).sort_values(["station_complex_id", "datetime"])
        station_frames = {
            sid: group.set_index("datetime")[["ridership", "transfers"]].sort_index()
            for sid, group in mta_data.groupby("station_complex_id")
        }
        print(f"[app.ml.inference] loaded trained model — {len(feature_columns)} features, {len(station_mapping)} stations, {len(mta_data)} historical readings")
    except Exception as exc:
        print(f"[app.ml.inference] historical MTA dataset unavailable, lag features will use current_passenger_count only: {exc}")
        station_frames = {}

    return model, feature_columns, station_mapping, station_metadata, station_frames


MODEL, FEATURE_COLUMNS, STATION_MAPPING, STATION_METADATA, STATION_FRAMES = _load_artifacts()


def get_station_metadata(station_id: str):
    station_id = str(station_id)
    rows = STATION_METADATA[STATION_METADATA["station_complex_id"].astype(str) == station_id]
    if rows.empty:
        raise ValueError(f"Station '{station_id}' not found in station metadata.")
    return rows.iloc[0]


def _nearest_reading(station_id: str, timestamp: pd.Timestamp, column: str):
    """Closest available real reading to `timestamp` for this station, in
    either direction, within MAX_READING_DISTANCE. None if the station has
    no historical data at all (true for all 9 Delhi stations — the
    dataset is NYC-only) or nothing close enough."""
    frame = STATION_FRAMES.get(str(station_id))
    if frame is None or frame.empty:
        return None
    idx = frame.index
    pos = idx.searchsorted(timestamp)
    candidates = [p for p in (pos - 1, pos) if 0 <= p < len(idx)]
    if not candidates:
        return None
    best = min(candidates, key=lambda p: abs(idx[p] - timestamp))
    if abs(idx[best] - timestamp) > MAX_READING_DISTANCE:
        return None
    return float(frame.iloc[best][column])


def build_features(station_id: str, timestamp, current_passenger_count: float = None) -> pd.DataFrame:
    """Build the exact feature row the trained model expects. Real
    historical readings are used wherever one is close enough to be
    trustworthy; current_passenger_count (from the request) covers the
    rest — always, for the 9 Delhi stations, since they have zero rows in
    the NYC-only historical dataset."""
    station_id = str(station_id)
    timestamp = pd.Timestamp(timestamp)

    if station_id not in STATION_MAPPING:
        raise ValueError(f"Station '{station_id}' not found in station mapping.")
    station_numeric = int(STATION_MAPPING[station_id])

    current_ridership = _nearest_reading(station_id, timestamp, "ridership")
    if current_ridership is None:
        if current_passenger_count is None:
            raise ValueError(f"No ridership data available for station '{station_id}' and no current_passenger_count fallback provided.")
        current_ridership = float(current_passenger_count)

    def lag(hours_back):
        v = _nearest_reading(station_id, timestamp - pd.Timedelta(hours=hours_back), "ridership")
        return v if v is not None else current_ridership

    lag_1h, lag_2h, lag_3h = lag(1), lag(2), lag(3)
    rolling_mean_3h = float(np.mean([lag_1h, lag_2h, lag_3h]))
    rolling_mean_6h = float(np.mean([lag(h) for h in range(1, 7)]))

    transfers = _nearest_reading(station_id, timestamp, "transfers")
    if transfers is None:
        transfers = 0.0

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

    station_info = get_station_metadata(station_id)
    latitude = float(station_info["latitude"])
    longitude = float(station_info["longitude"])

    features = {
        "ridership": current_ridership,
        "ridership_lag_1h": lag_1h,
        "ridership_lag_2h": lag_2h,
        "ridership_lag_3h": lag_3h,
        "rolling_mean_3h": rolling_mean_3h,
        "rolling_mean_6h": rolling_mean_6h,
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
        "transfers": transfers,
        "station_id_numeric": station_numeric,
    }
    return pd.DataFrame([[features[column] for column in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)


def predict_ridership(station_id: str, timestamp, current_passenger_count: float = None) -> float:
    if MODEL is None:
        raise RuntimeError("trained model artifacts are not available")
    X = build_features(station_id, timestamp, current_passenger_count=current_passenger_count)
    prediction = MODEL.predict(X)[0]
    return max(0.0, float(prediction))
