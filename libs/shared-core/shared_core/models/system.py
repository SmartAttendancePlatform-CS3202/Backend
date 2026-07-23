import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .identity import User
from sqlalchemy import String, Boolean, DateTime, func, ForeignKey, SmallInteger, Text, text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ENUM, JSONB, INET

from .base import Base
from .enums import AlertType


class SystemAlert(Base):
    __tablename__ = "system_alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    title: Mapped[str | None] = mapped_column(Text)
    type: Mapped[AlertType] = mapped_column(ENUM(AlertType, name="alert_type", create_type=False), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    old_data: Mapped[dict | None] = mapped_column(JSONB)
    new_data: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(INET)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(foreign_keys=[user_id])


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    id: Mapped[str] = mapped_column(String, primary_key=True, server_default="default")
    university_name: Mapped[str | None] = mapped_column(String)
    support_email: Mapped[str | None] = mapped_column(String)
    auto_approve_registrations: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    current_academic_year: Mapped[str | None] = mapped_column(String)
    default_late_threshold_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("10"))
    default_random_window_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("10"))
    default_geofence_radius_meters: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("30"))
    extra_config: Mapped[dict | None] = mapped_column(JSONB)


class AlembicVersion(Base):
    __tablename__ = "alembic_version"

    version_num: Mapped[str] = mapped_column(String, primary_key=True)
