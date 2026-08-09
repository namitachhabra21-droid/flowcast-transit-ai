from typing import List, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Identity is owned by Clerk; this row is a local mirror synced lazily
    from verified session claims so other tables can foreign-key against it."""

    __tablename__ = "users"

    clerk_user_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    memberships: Mapped[List["OrgMembership"]] = relationship(back_populates="user", cascade="all, delete-orphan")
