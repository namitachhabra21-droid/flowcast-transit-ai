import uuid

from pydantic import BaseModel, ConfigDict

from app.models import OrgRole, PlanTier


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan_tier: PlanTier


class MeOut(BaseModel):
    organization: OrganizationOut
    role: OrgRole
    auth_method: str
