import enum
import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OrgRole(str, enum.Enum):
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


# Authorization decisions (what a member is allowed to do) live here, not in
# Clerk — Clerk's org_role claim only tells us "admin vs member" and custom
# roles are a paid-tier feature. Keeping role in our own DB means RBAC is
# ours to test and evolve independent of the auth vendor.
ROLE_RANK = {OrgRole.viewer: 0, OrgRole.editor: 1, OrgRole.admin: 2}


class OrgMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "org_memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[OrgRole] = mapped_column(default=OrgRole.viewer, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")
