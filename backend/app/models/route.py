import enum
import uuid
from typing import List

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RouteSource(str, enum.Enum):
    synthetic = "synthetic"
    gtfs = "gtfs"


class Route(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "routes"
    __table_args__ = (UniqueConstraint("organization_id", "external_id", name="uq_route_org_external_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    headway_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    source: Mapped[RouteSource] = mapped_column(default=RouteSource.synthetic, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="routes")
    route_stops: Mapped[List["RouteStop"]] = relationship(
        back_populates="route", cascade="all, delete-orphan", order_by="RouteStop.sequence"
    )
    trips: Mapped[List["Trip"]] = relationship(back_populates="route", cascade="all, delete-orphan")
