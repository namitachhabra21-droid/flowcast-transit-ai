from fastapi import APIRouter, Depends

from app.auth.dependencies import Principal, get_current_organization, get_current_principal
from app.models import Organization
from app.schemas.organization import MeOut, OrganizationOut

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.get("/me", response_model=MeOut)
def get_my_org(
    principal: Principal = Depends(get_current_principal),
    org: Organization = Depends(get_current_organization),
) -> MeOut:
    return MeOut(
        organization=OrganizationOut.model_validate(org), role=principal.role, auth_method=principal.auth_method
    )
