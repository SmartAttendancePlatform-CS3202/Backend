import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .courses import RecordingLink, CourseOffering
    from .identity import User, Student
from sqlalchemy import String, Boolean, DateTime, func, ForeignKey, SmallInteger, Text, text, Integer, Numeric, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ENUM, JSONB

from .base import Base
from .enums import GeofenceShape, VerificationMethod, SessionStatus, WindowType, AttemptStatus, AttendanceStatus


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    building: Mapped[str | None] = mapped_column(String)
    floor: Mapped[str | None] = mapped_column(String)
    shape_type: Mapped[GeofenceShape] = mapped_column(ENUM(GeofenceShape, name="geofence_shape", create_type=False), nullable=False, server_default="circle")
    boundary_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    wifi_ssid: Mapped[str | None] = mapped_column(String)
    wifi_bssid: Mapped[str | None] = mapped_column(String)
    default_verification_method: Mapped[VerificationMethod] = mapped_column(ENUM(VerificationMethod, name="verification_method", create_type=False), nullable=False, server_default="gps_geofence")
    capacity: Mapped[int | None] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    course_offerings: Mapped[list["CourseOffering"]] = relationship(back_populates="venue")
    lecture_sessions: Mapped[list["LectureSession"]] = relationship(back_populates="venue")


class LectureSession(Base):
    __tablename__ = "lecture_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    course_offering_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("course_offerings.id"), nullable=False)
    venue_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("venues.id"))
    verification_method_override: Mapped[VerificationMethod | None] = mapped_column(ENUM(VerificationMethod, name="verification_method", create_type=False))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_mins: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(ENUM(SessionStatus, name="session_status", create_type=False), nullable=False, server_default="scheduled")
    held_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    session_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    course_offering: Mapped["CourseOffering"] = relationship(back_populates="lecture_sessions")
    venue: Mapped["Venue"] = relationship(back_populates="lecture_sessions")
    recording_links: Mapped[list["RecordingLink"]] = relationship(back_populates="lecture_session")
    verification_windows: Mapped[list["VerificationWindow"]] = relationship(back_populates="lecture_session")
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(back_populates="lecture_session")


class VerificationWindow(Base):
    __tablename__ = "verification_windows"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    lecture_session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lecture_sessions.id"), nullable=False)
    window_type: Mapped[WindowType] = mapped_column(ENUM(WindowType, name="window_type", create_type=False), nullable=False)
    scheduled_open_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("verification_windows_session_idx", "lecture_session_id"),
    )

    # Relationships
    lecture_session: Mapped["LectureSession"] = relationship(back_populates="verification_windows")
    attempts: Mapped[list["AttendanceVerificationAttempt"]] = relationship(back_populates="verification_window")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    lecture_session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lecture_sessions.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(ENUM(AttendanceStatus, name="attendance_status", create_type=False), nullable=False, server_default="absent")
    first_check_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    random_check_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    flag_reason: Mapped[str | None] = mapped_column(Text)
    is_manually_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    override_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    override_reason: Mapped[str | None] = mapped_column(Text)
    overridden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("lecture_session_id", "student_id", name="attendance_records_unique"),
    )

    # Relationships
    lecture_session: Mapped["LectureSession"] = relationship(back_populates="attendance_records")
    student: Mapped["Student"] = relationship(back_populates="attendance_records")
    overrider: Mapped["User"] = relationship(foreign_keys=[override_by])


class AttendanceVerificationAttempt(Base):
    __tablename__ = "attendance_verification_attempts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    verification_window_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("verification_windows.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    used_face_verification: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    used_location_check: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    location_method: Mapped[VerificationMethod | None] = mapped_column(ENUM(VerificationMethod, name="verification_method", create_type=False))
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    distance_from_venue_meters: Mapped[float | None] = mapped_column(Numeric)
    wifi_ssid_detected: Mapped[str | None] = mapped_column(String)
    face_match_confidence: Mapped[float | None] = mapped_column(Numeric)
    status: Mapped[AttemptStatus] = mapped_column(ENUM(AttemptStatus, name="attempt_status", create_type=False), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    device_info: Mapped[dict | None] = mapped_column(JSONB)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("attendance_verification_attempts_window_student_idx", "verification_window_id", "student_id"),
        Index("attendance_verification_attempts_student_time_idx", "student_id", "attempted_at"),
    )

    # Relationships
    verification_window: Mapped["VerificationWindow"] = relationship(back_populates="attempts")
    student: Mapped["Student"] = relationship(back_populates="verification_attempts")
