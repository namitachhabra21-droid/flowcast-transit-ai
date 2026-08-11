"""Route discovery + recommendation: POST /recommend-route.

This is the piece the audit found missing entirely: given a source and a
destination, find the viable routes between them, predict crowding for
EACH one (via the same heuristic /predict uses), compare them, and return
a recommendation with a reason — not just a single route's crowding.

Mounted at the app root, same tier as /predict: an internal endpoint the
frontend calls directly, not gated by the org-scoped Clerk/API-key auth
used under /api/v1.

Station/line data mirrors frontend/app.js's `stations` array exactly (same
names, same line memberships) so a route returned here corresponds to what
the user sees drawn on the network map — this is deliberately independent
from app/data/synthetic_data.py's station set, which belongs to the
separate org-scoped TransitPulse product under /api/v1.
"""
import hashlib
import math
import time
from datetime import datetime, timezone
from itertools import combinations
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.predict import PredictionFactor, PredictionRequest, predict_best_effort

router = APIRouter(tags=["ml"])

DEFAULT_CAPACITY = 60
TRANSFER_PENALTY_MINUTES = 8
MINUTES_PER_HOP = 4
LOAD_DRIFT_BUCKET_SECONDS = 6  # how often the "current load" reading is allowed to move

# ---- Station/line graph — mirrors frontend/app.js `stations` exactly ----

LINES = {
    "BLUE": "Blue Line",
    "YELLOW": "Yellow Line",
    "VIOLET": "Violet Line",
    "MAGENTA": "Magenta Line",
    "AIRPORT": "Airport Express",
}

STATIONS: Dict[str, Dict] = {
    "rajiv-chowk": {"name": "Rajiv Chowk", "lines": ["BLUE", "YELLOW"]},
    "kashmere-gate": {"name": "Kashmere Gate", "lines": ["YELLOW", "VIOLET"]},
    "new-delhi": {"name": "New Delhi", "lines": ["YELLOW", "AIRPORT"]},
    "central-secretariat": {"name": "Central Secretariat", "lines": ["YELLOW", "VIOLET"]},
    "noida-sector-18": {"name": "Noida Sector 18", "lines": ["BLUE"]},
    "dwarka-sector-21": {"name": "Dwarka Sector 21", "lines": ["BLUE", "AIRPORT"]},
    "hauz-khas": {"name": "Hauz Khas", "lines": ["YELLOW", "MAGENTA"]},
    "botanical-garden": {"name": "Botanical Garden", "lines": ["BLUE", "MAGENTA"]},
    "igi-airport": {"name": "IGI Airport", "lines": ["AIRPORT"]},
}

STATIONS_BY_LINE: Dict[str, List[str]] = {
    line: [sid for sid, s in STATIONS.items() if line in s["lines"]] for line in LINES
}


class StationOut(BaseModel):
    id: str
    name: str
    lines: List[str]


@router.get("/stations", response_model=List[StationOut])
def list_stations():
    """So the frontend's From/To selects can be populated from the same
    source of truth as route discovery, instead of a second hardcoded list."""
    return [StationOut(id=sid, name=s["name"], lines=s["lines"]) for sid, s in STATIONS.items()]


class RecommendRequest(BaseModel):
    source_station: str = Field(..., description="Station id, e.g. 'rajiv-chowk'")
    destination_station: str = Field(..., description="Station id, e.g. 'dwarka-sector-21'")
    departure_time: Optional[datetime] = Field(None, description="Defaults to now if omitted")


class EvaluatedRoute(BaseModel):
    route_id: str
    route_name: str
    transfer_station: Optional[str] = None
    estimated_travel_time_minutes: int
    current_data: dict
    predicted_passenger_count: int
    predicted_occupancy_percentage: float
    crowding_level: str
    confidence: float
    factors: List[PredictionFactor]


class RecommendResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    source_station: str
    destination_station: str
    departure_time: datetime
    evaluated_routes: List[EvaluatedRoute]
    recommended_route_id: Optional[str]
    recommendation_reason: str
    model_version: str


def _base_current_load(line: str, station_id: str, *, now: Optional[datetime] = None) -> int:
    """Stand-in for a real ticketing-system read: a per-line/station
    baseline (hash-seeded, same pattern app/data/synthetic_data.py uses)
    shaped by an actual rush-hour curve against the real clock, plus a
    short-period drift term that only moves every LOAD_DRIFT_BUCKET_SECONDS
    — so it behaves like a live feed being sampled, not a random number."""
    now = now or datetime.now(timezone.utc)
    digest = hashlib.sha256(f"{line}:{station_id}".encode()).hexdigest()
    variance = (int(digest[:8], 16) % 1000) / 1000  # 0..1
    line_popularity = {"BLUE": 0.55, "YELLOW": 0.7, "VIOLET": 0.45, "MAGENTA": 0.4, "AIRPORT": 0.35}
    base = line_popularity.get(line, 0.5)

    hour_frac = now.hour + now.minute / 60
    morning_peak = math.exp(-((hour_frac - 8.5) ** 2) / 8)
    evening_peak = math.exp(-((hour_frac - 18.5) ** 2) / 8)
    rush_hour_wave = 0.3 * (morning_peak + evening_peak)

    bucket = int(now.timestamp() // LOAD_DRIFT_BUCKET_SECONDS)
    drift_digest = hashlib.sha256(f"{line}:{station_id}:{bucket}".encode()).hexdigest()
    drift = ((int(drift_digest[:8], 16) % 1000) / 1000 - 0.5) * 0.14  # +/-7%

    ratio = min(0.97, max(0.05, 0.2 + base * 0.35 + variance * 0.2 + rush_hour_wave + drift))
    return round(ratio * DEFAULT_CAPACITY)


def _find_candidate_routes(source_id: str, dest_id: str) -> List[dict]:
    """Direct routes (shared line) + single-transfer routes (source's line
    and dest's line share a common station). Caps at 2+ transfers — a
    reasonable hackathon-scoped limit, noted in the README as a next step."""
    source_lines = set(STATIONS[source_id]["lines"])
    dest_lines = set(STATIONS[dest_id]["lines"])

    candidates = []

    for line in source_lines & dest_lines:
        candidates.append({"lines": [line], "transfer_station": None})

    for line_a, line_b in combinations(source_lines | dest_lines, 2):
        stations_a = set(STATIONS_BY_LINE.get(line_a, []))
        stations_b = set(STATIONS_BY_LINE.get(line_b, []))
        if line_a in source_lines and line_b in dest_lines:
            shared = stations_a & stations_b
            for transfer_id in shared:
                if transfer_id not in (source_id, dest_id):
                    candidates.append({"lines": [line_a, line_b], "transfer_station": transfer_id})
        if line_b in source_lines and line_a in dest_lines:
            shared = stations_a & stations_b
            for transfer_id in shared:
                if transfer_id not in (source_id, dest_id):
                    candidates.append({"lines": [line_b, line_a], "transfer_station": transfer_id})

    # de-dupe (same line combo + transfer point can surface twice from the loop above)
    seen = set()
    unique = []
    for c in candidates:
        key = (tuple(c["lines"]), c["transfer_station"])
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


@router.post("/recommend-route", response_model=RecommendResponse)
def recommend_route(payload: RecommendRequest) -> RecommendResponse:
    if payload.source_station not in STATIONS:
        raise HTTPException(status_code=404, detail=f"Unknown source_station '{payload.source_station}'")
    if payload.destination_station not in STATIONS:
        raise HTTPException(status_code=404, detail=f"Unknown destination_station '{payload.destination_station}'")
    if payload.source_station == payload.destination_station:
        raise HTTPException(status_code=400, detail="source_station and destination_station must differ")

    departure_time = payload.departure_time or datetime.now(timezone.utc)
    candidates = _find_candidate_routes(payload.source_station, payload.destination_station)
    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No route found between '{payload.source_station}' and '{payload.destination_station}'",
        )

    evaluated: List[EvaluatedRoute] = []
    route_model_version = None
    for candidate in candidates:
        boarding_line = candidate["lines"][0]
        current_count = _base_current_load(boarding_line, payload.source_station)

        # Reuses the exact same trained-model-then-heuristic-fallback path
        # /predict exposes — one prediction per candidate route, not one
        # prediction reused for all of them.
        pred_request = PredictionRequest(
            route_id=boarding_line,
            station_id=payload.source_station,
            vehicle_capacity=DEFAULT_CAPACITY,
            current_passenger_count=current_count,
            timestamp=departure_time,
        )
        predicted_count, occupancy_pct, level, confidence, factors, route_model_version = predict_best_effort(pred_request)

        hops = 2 if candidate["transfer_station"] else 1
        travel_time = hops * MINUTES_PER_HOP * 3 + (TRANSFER_PENALTY_MINUTES if candidate["transfer_station"] else 0)

        line_names = " + ".join(LINES[l] for l in candidate["lines"])
        route_id = "-".join(candidate["lines"]) + (f"-via-{candidate['transfer_station']}" if candidate["transfer_station"] else "")

        evaluated.append(
            EvaluatedRoute(
                route_id=route_id,
                route_name=line_names,
                transfer_station=STATIONS[candidate["transfer_station"]]["name"] if candidate["transfer_station"] else None,
                estimated_travel_time_minutes=travel_time,
                current_data={"current_passenger_count": current_count, "vehicle_capacity": DEFAULT_CAPACITY},
                predicted_passenger_count=predicted_count,
                predicted_occupancy_percentage=occupancy_pct,
                crowding_level=level.value,
                confidence=confidence,
                factors=factors,
            )
        )

    evaluated.sort(key=lambda r: r.predicted_occupancy_percentage)
    best = evaluated[0]

    if len(evaluated) > 1:
        runner_up = min(evaluated[1:], key=lambda r: r.predicted_occupancy_percentage)
        diff_pct = round(((runner_up.predicted_occupancy_percentage - best.predicted_occupancy_percentage) / runner_up.predicted_occupancy_percentage) * 100)
        if diff_pct > 0:
            reason = (
                f"{best.route_name} has {diff_pct}% lower predicted occupancy than "
                f"{runner_up.route_name} ({best.predicted_occupancy_percentage}% vs "
                f"{runner_up.predicted_occupancy_percentage}%)."
            )
        else:
            reason = f"{best.route_name} has the lowest predicted occupancy among the {len(evaluated)} routes evaluated."
    else:
        reason = f"{best.route_name} is the only viable route between these stations."

    reason += f" Model confidence: {round(best.confidence * 100)}%."

    return RecommendResponse(
        source_station=STATIONS[payload.source_station]["name"],
        destination_station=STATIONS[payload.destination_station]["name"],
        departure_time=departure_time,
        evaluated_routes=evaluated,
        recommended_route_id=best.route_id,
        recommendation_reason=reason,
        model_version=route_model_version,
    )
