import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.api_key import generate_api_key
from app.auth.dependencies import Principal, require_role
from app.db.session import get_db
from app.models import ApiKey, OrgRole
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyOut

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=List[ApiKeyOut])
def list_api_keys(principal: Principal = Depends(require_role(OrgRole.admin)), db: Session = Depends(get_db)):
    return (
        db.query(ApiKey)
        .filter(ApiKey.organization_id == principal.organization_id, ApiKey.revoked_at.is_(None))
        .order_by(ApiKey.created_at.desc())
        .all()
    )


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreate,
    principal: Principal = Depends(require_role(OrgRole.admin)),
    db: Session = Depends(get_db),
):
    plaintext, key_prefix, key_hash = generate_api_key()
    api_key = ApiKey(
        organization_id=principal.organization_id,
        created_by_user_id=principal.user_id,
        name=payload.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return ApiKeyCreated(**ApiKeyOut.model_validate(api_key).model_dump(), key=plaintext)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: uuid.UUID,
    principal: Principal = Depends(require_role(OrgRole.admin)),
    db: Session = Depends(get_db),
):
    api_key = (
        db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.organization_id == principal.organization_id).one_or_none()
    )
    if api_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    api_key.revoked_at = datetime.now(timezone.utc)
    db.commit()
