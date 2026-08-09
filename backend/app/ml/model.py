"""
Rule-based crowding heuristic.

predicted_score = base_load x time_of_day_multiplier x day_of_week_multiplier (+ noise)

This is the only module that knows how a crowding prediction is computed. It
depends on `synthetic_data.get_base_load` for the ridership baseline but
nothing else in the app depends on how the score itself is derived.

`predict()` is the seam a future model registry hooks into: swap this
function's body for a trained model lookup (e.g. per-org LightGBM) and keep
the same (org_id, route_id, stop_id, timestamp) -> {score, level, model_version}
contract, and no caller has to change.
"""
import math
import random
from datetime import datetime
from typing import Dict

from app.data import synthetic_data

MODEL_VERSION = "heuristic-v1"

LEVEL_THRESHOLDS = [
    (0.40, "low"),
    (0.70, "medium"),
    (1.00, "high"),
    (float("inf"), "full"),
]


def _gaussian(x: float, mu: float, sigma: float) -> float:
    return math.exp(-((x - mu) ** 2) / (2 * sigma ** 2))


def time_of_day_multiplier(dt: datetime) -> float:
    """Peaks around 8am and 6pm, quiet late night / midday trough."""
    hour = dt.hour + dt.minute / 60
    morning_peak = _gaussian(hour, mu=8.0, sigma=1.1)
    evening_peak = _gaussian(hour, mu=18.0, sigma=1.3)
    return 0.35 + 1.3 * morning_peak + 1.45 * evening_peak


def day_of_week_multiplier(dt: datetime) -> float:
    weekday = dt.weekday()  # 0=Mon .. 6=Sun
    if weekday == 5:
        return 0.6  # Saturday
    if weekday == 6:
        return 0.5  # Sunday
    return 1.0


def _score_to_level(score: float) -> str:
    for threshold, level in LEVEL_THRESHOLDS:
        if score < threshold:
            return level
    return "full"


def predict(org_id: str, route_external_id: str, stop_external_id: str, timestamp: datetime) -> Dict:
    base_load = synthetic_data.get_base_load(org_id, route_external_id, stop_external_id)
    tod_mult = time_of_day_multiplier(timestamp)
    dow_mult = day_of_week_multiplier(timestamp)
    noise = random.uniform(-0.08, 0.08)
    score = max(0.0, base_load * tod_mult * dow_mult + noise)
    return {"score": round(score, 3), "level": _score_to_level(score), "model_version": MODEL_VERSION}
