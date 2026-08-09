"""
Synthetic GTFS-style transit data provider.

Generates fake-but-plausible routes, stops, and trip schedules, plus a
deterministic "base ridership load" per org/route/stop. This module exposes
a small provider interface, every function taking `org_id` first so a real
feed-backed implementation can pick the right tenant's feed URL/config:

    list_routes(org_id)
    list_stops_for_route(org_id, route_id)
    list_trips_for_route(org_id, route_id, now=None, limit=8)
    get_trip(org_id, trip_id)
    get_base_load(org_id, route_id, stop_id)

A future real-data integration (e.g. a GTFS-RT feed poller, keyed off each
org's configured feed URL) should implement the same function signatures in
its own module. The seeding/prediction service layer only depends on this
interface, so swapping the implementation is a one-line import change and
nothing else has to move. The synthetic implementation ignores `org_id` for
the route/stop catalog (every trial org sees the same demo network) but
mixes it into `get_base_load` so tenants still see distinct numbers.
"""
import hashlib
from datetime import datetime, timedelta, date, time as dtime
from typing import List, Optional

STOPS = {
    "downtown": "Downtown Central",
    "elm": "Elm Street",
    "oak": "Oak & 5th",
    "maple": "Maple Heights",
    "pine": "Pine Crossing",
    "riverside": "Riverside Park",
    "harbor": "Harbor Terminal",
    "university": "University Ave",
    "market": "Market Square",
    "hillcrest": "Hillcrest",
    "airport": "Airport Terminal",
    "stadium": "Stadium Gate",
}

ROUTES = [
    {
        "id": "R1",
        "name": "Red Line",
        "stops": ["downtown", "elm", "oak", "maple", "pine", "riverside"],
        "headway_minutes": 12,
        "popularity": 0.85,
    },
    {
        "id": "B2",
        "name": "Blue Line",
        "stops": ["harbor", "downtown", "market", "university", "hillcrest"],
        "headway_minutes": 15,
        "popularity": 0.7,
    },
    {
        "id": "G3",
        "name": "Green Express",
        "stops": ["downtown", "market", "stadium", "airport"],
        "headway_minutes": 20,
        "popularity": 0.6,
    },
    {
        "id": "Y4",
        "name": "Yellow Loop",
        "stops": ["university", "oak", "maple", "hillcrest", "riverside", "downtown"],
        "headway_minutes": 18,
        "popularity": 0.5,
    },
]

SERVICE_START = dtime(5, 0)
SERVICE_END = dtime(23, 30)
STOP_TRAVEL_MINUTES = 3  # approximate time between consecutive stops


def _route_by_id(route_id: str) -> Optional[dict]:
    return next((r for r in ROUTES if r["id"] == route_id), None)


def list_routes(org_id: str) -> List[dict]:
    return [{"id": r["id"], "name": r["name"], "headway_minutes": r["headway_minutes"]} for r in ROUTES]


def list_stops_for_route(org_id: str, route_id: str) -> Optional[List[dict]]:
    route = _route_by_id(route_id)
    if not route:
        return None
    return [{"id": sid, "name": STOPS[sid]} for sid in route["stops"]]


def _generate_day_trips(route: dict, service_date: date) -> List[dict]:
    trips = []
    current = datetime.combine(service_date, SERVICE_START)
    end = datetime.combine(service_date, SERVICE_END)
    while current <= end:
        trip_id = f"{route['id']}_{service_date.isoformat()}_{current.strftime('%H%M')}"
        stop_times = []
        stop_time = current
        for sid in route["stops"]:
            stop_times.append({
                "stop_id": sid,
                "stop_name": STOPS[sid],
                "scheduled_time": stop_time,
            })
            stop_time += timedelta(minutes=STOP_TRAVEL_MINUTES)
        trips.append({
            "id": trip_id,
            "route_id": route["id"],
            "route_name": route["name"],
            "departure_time": current,
            "stop_times": stop_times,
        })
        current += timedelta(minutes=route["headway_minutes"])
    return trips


def list_trips_for_route(
    org_id: str, route_id: str, now: Optional[datetime] = None, limit: int = 8
) -> Optional[List[dict]]:
    route = _route_by_id(route_id)
    if not route:
        return None
    now = now or datetime.now()
    upcoming = [t for t in _generate_day_trips(route, now.date()) if t["departure_time"] >= now]
    if len(upcoming) < limit:
        upcoming += _generate_day_trips(route, now.date() + timedelta(days=1))
    return upcoming[:limit]


def get_trip(org_id: str, trip_id: str) -> Optional[dict]:
    try:
        route_id, date_str, _hhmm = trip_id.split("_")
        service_date = date.fromisoformat(date_str)
    except ValueError:
        return None
    route = _route_by_id(route_id)
    if not route:
        return None
    return next((t for t in _generate_day_trips(route, service_date) if t["id"] == trip_id), None)


def get_base_load(org_id: str, route_id: str, stop_id: str) -> float:
    """
    Deterministic 'typical demand' baseline for an org/route/stop combo,
    standing in for a historical ridership average. Swap for a real
    historical lookup once live data is available; the (0..1) return
    contract is what model.py relies on.
    """
    route = _route_by_id(route_id)
    popularity = route["popularity"] if route else 0.6
    digest = hashlib.sha256(f"{org_id}:{route_id}:{stop_id}".encode()).hexdigest()
    stop_variance = (int(digest[:8], 16) % 1000) / 1000  # deterministic 0..1
    hub_boost = 0.15 if stop_id in ("downtown", "market", "harbor") else 0.0
    return min(1.0, 0.25 + popularity * 0.4 + stop_variance * 0.3 + hub_boost)
