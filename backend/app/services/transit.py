"""Ties the swappable data/model layer (app/data, app/ml) to persisted
state. These functions are written to be the eventual APScheduler refresh
job's body verbatim — for now the API layer calls them synchronously,
on-demand, per request, which is enough to prove the DB + auth foundation
end-to-end without standing up a scheduler yet.
"""
from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy.orm import Session

from app.data import synthetic_data
from app.ml import model
from app.models import CrowdingPrediction, Organization, Route, RouteStop, Stop, Trip, TripStopTime

TRIPS_PER_ROUTE = 6


def ensure_org_seeded(db: Session, org: Organization) -> None:
    """Populates routes/stops for a trial org the first time they're needed.
    A future GTFS-backed org would populate these from a real static feed
    import instead — this function is the seam."""
    if db.query(Route.id).filter(Route.organization_id == org.id).first() is not None:
        return

    org_id_str = str(org.id)
    stop_by_external_id: Dict[str, Stop] = {}
    for route_data in synthetic_data.list_routes(org_id_str):
        route = Route(
            organization_id=org.id,
            external_id=route_data["id"],
            name=route_data["name"],
            headway_minutes=route_data["headway_minutes"],
        )
        db.add(route)
        db.flush()

        stop_rows = synthetic_data.list_stops_for_route(org_id_str, route_data["id"]) or []
        for sequence, stop_data in enumerate(stop_rows):
            stop = stop_by_external_id.get(stop_data["id"])
            if stop is None:
                stop = Stop(organization_id=org.id, external_id=stop_data["id"], name=stop_data["name"])
                db.add(stop)
                db.flush()
                stop_by_external_id[stop_data["id"]] = stop
            db.add(RouteStop(route_id=route.id, stop_id=stop.id, sequence=sequence))
    db.commit()


def ensure_upcoming_trips(db: Session, org: Organization, route: Route) -> List[Trip]:
    """Idempotent: re-running for a window that's already persisted just
    returns the existing rows (trips are keyed by org + external_id)."""
    org_id_str = str(org.id)
    stops_by_external_id = {s.external_id: s for s in db.query(Stop).filter(Stop.organization_id == org.id).all()}
    source_trips = synthetic_data.list_trips_for_route(org_id_str, route.external_id, limit=TRIPS_PER_ROUTE) or []

    trips: List[Trip] = []
    for trip_data in source_trips:
        trip = (
            db.query(Trip).filter(Trip.organization_id == org.id, Trip.external_id == trip_data["id"]).one_or_none()
        )
        if trip is None:
            trip = Trip(
                organization_id=org.id,
                route_id=route.id,
                external_id=trip_data["id"],
                service_date=trip_data["departure_time"].date(),
                departure_time=trip_data["departure_time"],
            )
            db.add(trip)
            db.flush()
            for sequence, stop_time in enumerate(trip_data["stop_times"]):
                stop = stops_by_external_id[stop_time["stop_id"]]
                db.add(
                    TripStopTime(
                        trip_id=trip.id,
                        stop_id=stop.id,
                        sequence=sequence,
                        scheduled_time=stop_time["scheduled_time"],
                    )
                )
            db.flush()
        trips.append(trip)
    db.commit()
    return trips


def refresh_crowding_predictions(db: Session, org: Organization, route: Route, trips: List[Trip]) -> None:
    """base_load x time-of-day x day-of-week, recomputed and upserted per
    (trip, stop) — this is the exact function an APScheduler job would call
    every N minutes per org instead of on each request."""
    now = datetime.now(timezone.utc)
    for trip in trips:
        for stop_time in trip.stop_times:
            prediction = model.predict(str(org.id), route.external_id, stop_time.stop.external_id, stop_time.scheduled_time)
            existing = (
                db.query(CrowdingPrediction)
                .filter(CrowdingPrediction.trip_id == trip.id, CrowdingPrediction.stop_id == stop_time.stop_id)
                .one_or_none()
            )
            if existing is None:
                db.add(
                    CrowdingPrediction(
                        organization_id=org.id,
                        trip_id=trip.id,
                        stop_id=stop_time.stop_id,
                        score=prediction["score"],
                        level=prediction["level"],
                        model_version=prediction["model_version"],
                        predicted_at=now,
                    )
                )
            else:
                existing.score = prediction["score"]
                existing.level = prediction["level"]
                existing.model_version = prediction["model_version"]
                existing.predicted_at = now
    db.commit()
