"""Resolves an incoming request to a `Principal` (organization + role) from
either a Clerk session (`Authorization: Bearer <clerk_jwt>`, dashboard) or
an API key (`X-API-Key: <key>`, programmatic access) — never both parsed
from the same header, so there's no ambiguity about which auth path fired.

RBAC decisions are made against our own `org_memberships.role`, not Clerk's
role claim (see models/membership.py for why).
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.api_key import hash_api_key
from app.auth.clerk import fetch_clerk_user, verify_session_token
from app.db.session import get_db
from app.models import ApiKey, OrgMembership, OrgRole, Organization, User
from app.models.membership import ROLE_RANK


@dataclass
class Principal:
    organization_id: uuid.UUID
    role: OrgRole
    auth_method: str  # "session" | "api_key"
    user_id: Optional[uuid.UUID] = None


def _get_or_create_user(db: Session, clerk_user_id: str) -> User:
    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).one_or_none()
    if user:
        return user
    profile = fetch_clerk_user(clerk_user_id)
    user = User(clerk_user_id=clerk_user_id, email=profile["email"], full_name=profile.get("full_name"))
    db.add(user)
    db.flush()
    return user


def _get_or_create_org(db: Session, clerk_org_id: str, org_slug: Optional[str]) -> Organization:
    org = db.query(Organization).filter(Organization.clerk_org_id == clerk_org_id).one_or_none()
    if org:
        return org
    label = org_slug or clerk_org_id
    org = Organization(name=label, slug=label, clerk_org_id=clerk_org_id)
    db.add(org)
    db.flush()
    return org


def _get_or_create_membership(db: Session, org: Organization, user: User, default_role: OrgRole) -> OrgMembership:
    membership = (
        db.query(OrgMembership)
        .filter(OrgMembership.organization_id == org.id, OrgMembership.user_id == user.id)
        .one_or_none()
    )
    if membership:
        return membership
    membership = OrgMembership(organization_id=org.id, user_id=user.id, role=default_role)
    db.add(membership)
    db.flush()
    return membership


def _resolve_session_principal(db: Session, token: str) -> Principal:
    claims = verify_session_token(token)
    if not claims.org_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No active organization on this session — select or create one in Clerk first.",
        )
    user = _get_or_create_user(db, claims.user_id)
    org = _get_or_create_org(db, claims.org_id, claims.org_slug)
    # First time we see this (user, org) pair: Clerk's own admin becomes our
    # admin, everyone else lands as editor and can be promoted/demoted later
    # via the members endpoint — our role table is authoritative from here on.
    default_role = OrgRole.admin if claims.org_role == "org:admin" else OrgRole.editor
    membership = _get_or_create_membership(db, org, user, default_role)
    db.commit()
    return Principal(organization_id=org.id, role=membership.role, auth_method="session", user_id=user.id)


def _resolve_api_key_principal(db: Session, key: str) -> Principal:
    api_key = db.query(ApiKey).filter(ApiKey.key_hash == hash_api_key(key)).one_or_none()
    if api_key is None or api_key.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or revoked API key")
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    # API keys are read-only by design: enough to call the crowding API,
    # never enough to manage members, billing, or other keys.
    return Principal(organization_id=api_key.organization_id, role=OrgRole.viewer, auth_method="api_key")


def get_current_principal(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> Principal:
    if x_api_key:
        return _resolve_api_key_principal(db, x_api_key)
    if authorization and authorization.lower().startswith("bearer "):
        return _resolve_session_principal(db, authorization.split(" ", 1)[1].strip())
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Missing credentials — send a Clerk session (Authorization: Bearer <token>) or an API key (X-API-Key).",
    )


def require_role(minimum: OrgRole):
    """Dependency factory: require at least `minimum` role (viewer < editor < admin)."""

    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if ROLE_RANK[principal.role] < ROLE_RANK[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires {minimum.value} role or higher")
        return principal

    return dependency


def get_current_organization(
    principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> Organization:
    org = db.get(Organization, principal.organization_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    return org
