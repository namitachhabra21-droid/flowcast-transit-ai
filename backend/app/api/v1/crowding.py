from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_organization
from app.db.session import get_db
from app.models import CrowdingPrediction, Organization, Trip, TripStopTime
from app.schemas.crowding import CrowdingStopOut, TripCrowdingOut
from app.services.transit import refresh_crowding_predictions

router = APIRouter(prefix="/trips", tags=["crowding"])


@router.get("/{trip_external_id}/crowding", response_model=TripCrowdingOut)
def get_trip_crowding(
    trip_external_id: str,
    org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    trip = (
        db.query(Trip)
        .options(joinedload(Trip.stop_times).joinedload(TripStopTime.stop), joinedload(Trip.route))
        .filter(Trip.organization_id == org.id, Trip.external_id == trip_external_id)
        .one_or_none()
    )
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")

    refresh_crowding_predictions(db, org, trip.route, [trip])

    predictions = {
        p.stop_id: p for p in db.query(CrowdingPrediction).filter(CrowdingPrediction.trip_id == trip.id).all()
    }
    stops = [
        CrowdingStopOut(
            stop_id=st.stop.external_id,
            stop_name=st.stop.name,
            scheduled_time=st.scheduled_time,
            score=predictions[st.stop_id].score,
            level=predictions[st.stop_id].level.value,
            model_version=predictions[st.stop_id].model_version,
        )
        for st in trip.stop_times
    ]
    return TripCrowdingOut(
        trip_id=trip.external_id,
        route_id=trip.route.external_id,
        generated_at=datetime.now(timezone.utc),
        stops=stops,
    )
