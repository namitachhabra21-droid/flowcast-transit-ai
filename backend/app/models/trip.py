import uuid
from datetime import date as date_, datetime
from typing import List

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Trip(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trips"
    __table_args__ = (UniqueConstraint("organization_id", "external_id", name="uq_trip_org_external_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    service_date: Mapped[date_] = mapped_column(Date, nullable=False)
    departure_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    route: Mapped["Route"] = relationship(back_populates="trips")
    stop_times: Mapped[List["TripStopTime"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", order_by="TripStopTime.sequence"
    )


class TripStopTime(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "trip_stop_times"
    __table_args__ = (UniqueConstraint("trip_id", "sequence", name="uq_trip_stop_sequence"),)

    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False
    )
    stop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stops.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    trip: Mapped["Trip"] = relationship(back_populates="stop_times")
    stop: Mapped["Stop"] = relationship()
