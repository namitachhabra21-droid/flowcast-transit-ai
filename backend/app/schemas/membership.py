import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models import OrgRole


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    role: OrgRole


class MemberRoleUpdate(BaseModel):
    role: OrgRole
