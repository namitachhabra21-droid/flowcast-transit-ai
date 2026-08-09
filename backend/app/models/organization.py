import enum
import uuid
from typing import List, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PlanTier(str, enum.Enum):
    trial = "trial"
    pro = "pro"
    enterprise = "enterprise"


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A tenant: one transit agency / city customer."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    clerk_org_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    plan_tier: Mapped[PlanTier] = mapped_column(default=PlanTier.trial, nullable=False)

    # None => no live feed configured, fall back to the synthetic generator.
    gtfs_static_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    gtfs_rt_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    memberships: Mapped[List["OrgMembership"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    routes: Mapped[List["Route"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    api_keys: Mapped[List["ApiKey"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
