"""Import every model so SQLAlchemy's mapper registry (and Alembic
autogenerate, which diffs against Base.metadata) sees the full schema."""

from app.models.api_key import ApiKey
from app.models.crowding_prediction import CrowdingLevel, CrowdingPrediction
from app.models.membership import OrgMembership, OrgRole
from app.models.organization import Organization, PlanTier
from app.models.route import Route, RouteSource
from app.models.stop import RouteStop, Stop
from app.models.trip import Trip, TripStopTime
from app.models.user import User

__all__ = [
    "ApiKey",
    "CrowdingLevel",
    "CrowdingPrediction",
    "OrgMembership",
    "OrgRole",
    "Organization",
    "PlanTier",
    "Route",
    "RouteSource",
    "RouteStop",
    "Stop",
    "Trip",
    "TripStopTime",
    "User",
]
