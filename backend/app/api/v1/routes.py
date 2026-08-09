from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_organization
from app.db.session import get_db
from app.models import Organization, Route
from app.schemas.route import RouteOut
from app.services.transit import ensure_org_seeded

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("", response_model=List[RouteOut])
def list_routes(org: Organization = Depends(get_current_organization), db: Session = Depends(get_db)):
    ensure_org_seeded(db, org)
    return db.query(Route).filter(Route.organization_id == org.id).order_by(Route.external_id).all()
