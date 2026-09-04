import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .identity import Student, User
from sqlalchemy import Boolean, DateTime, func, ForeignKey, Text, text, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from .base import Base


class FaceProfile(Base):
    __tablename__ = "face_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    embedding: Mapped[Any] = mapped_column(Vector(192), nullable=False)
    reference_photo_url: Mapped[str] = mapped_column(Text, nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Numeric)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    __table_args__ = (
        Index("face_profiles_active_unique", "student_id", unique=True, postgresql_where=text("is_active = true")),
    )

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="face_profile")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
