import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class ApiKeyCreated(ApiKeyOut):
    key: str  # plaintext — shown exactly once, at creation
