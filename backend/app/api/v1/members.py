import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import Principal, get_current_principal, require_role
from app.db.session import get_db
from app.models import OrgMembership, OrgRole
from app.schemas.membership import MemberOut, MemberRoleUpdate

router = APIRouter(prefix="/members", tags=["members"])


def _to_member_out(membership: OrgMembership) -> MemberOut:
    return MemberOut(
        user_id=membership.user_id, email=membership.user.email, full_name=membership.user.full_name, role=membership.role
    )


@router.get("", response_model=List[MemberOut])
def list_members(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)):
    memberships = (
        db.query(OrgMembership)
        .options(joinedload(OrgMembership.user))
        .filter(OrgMembership.organization_id == principal.organization_id)
        .all()
    )
    return [_to_member_out(m) for m in memberships]


@router.patch("/{user_id}", response_model=MemberOut)
def update_member_role(
    user_id: uuid.UUID,
    payload: MemberRoleUpdate,
    principal: Principal = Depends(require_role(OrgRole.admin)),
    db: Session = Depends(get_db),
):
    membership = (
        db.query(OrgMembership)
        .options(joinedload(OrgMembership.user))
        .filter(OrgMembership.organization_id == principal.organization_id, OrgMembership.user_id == user_id)
        .one_or_none()
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    membership.role = payload.role
    db.commit()
    db.refresh(membership)
    return _to_member_out(membership)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: uuid.UUID,
    principal: Principal = Depends(require_role(OrgRole.admin)),
    db: Session = Depends(get_db),
):
    if user_id == principal.user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot remove yourself")
    membership = (
        db.query(OrgMembership)
        .filter(OrgMembership.organization_id == principal.organization_id, OrgMembership.user_id == user_id)
        .one_or_none()
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    db.delete(membership)
    db.commit()
