from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_organization
from app.db.session import get_db
from app.models import Organization, Route
from app.schemas.trip import TripOut, TripStopOut
from app.services.transit import ensure_org_seeded, ensure_upcoming_trips, refresh_crowding_predictions

router = APIRouter(prefix="/routes", tags=["trips"])


@router.get("/{route_external_id}/trips", response_model=List[TripOut])
def list_trips(
    route_external_id: str,
    org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    ensure_org_seeded(db, org)
    route = (
        db.query(Route)
        .filter(Route.organization_id == org.id, Route.external_id == route_external_id)
        .one_or_none()
    )
    if route is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Route not found")

    trips = ensure_upcoming_trips(db, org, route)
    refresh_crowding_predictions(db, org, route, trips)

    return [
        TripOut(
            id=trip.external_id,
            route_id=route.external_id,
            route_name=route.name,
            departure_time=trip.departure_time,
            stops=[
                TripStopOut(id=st.stop.external_id, name=st.stop.name, scheduled_time=st.scheduled_time)
                for st in trip.stop_times
            ],
        )
        for trip in trips
    ]
