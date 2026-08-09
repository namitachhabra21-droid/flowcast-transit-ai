import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class CrowdingLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    full = "full"


class CrowdingPrediction(UUIDPrimaryKeyMixin, Base):
    """Current predicted crowding for a (trip, stop) pair. Upserted on each
    refresh cycle rather than accumulated indefinitely — a history/audit
    table can be added later if predictions need to feed model training."""

    __tablename__ = "crowding_predictions"
    __table_args__ = (UniqueConstraint("trip_id", "stop_id", name="uq_crowding_trip_stop"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False
    )
    stop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stops.id", ondelete="CASCADE"), nullable=False
    )

    score: Mapped[float] = mapped_column(Float, nullable=False)
    level: Mapped[CrowdingLevel] = mapped_column(nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
