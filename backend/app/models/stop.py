import uuid
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Stop(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stops"
    __table_args__ = (UniqueConstraint("organization_id", "external_id", name="uq_stop_org_external_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class RouteStop(UUIDPrimaryKeyMixin, Base):
    """Defines a route's ordered stop sequence."""

    __tablename__ = "route_stops"
    __table_args__ = (UniqueConstraint("route_id", "sequence", name="uq_route_stop_sequence"),)

    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )
    stop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stops.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    route: Mapped["Route"] = relationship(back_populates="route_stops")
    stop: Mapped["Stop"] = relationship()
