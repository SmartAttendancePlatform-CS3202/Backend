import uuid
from datetime import datetime, date, time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .identity import Student, User, Lecturer, AcademicYear, Department
    from .attendance import LectureSession, Venue
from sqlalchemy import String, Boolean, DateTime, func, ForeignKey, SmallInteger, Text, text, Integer, Date, Time, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ENUM, ARRAY as PG_ARRAY

from .base import Base
from .enums import NoticeUrgency, RecordingPlatform, UserRole


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    course_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id"))
    credits: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    department: Mapped["Department"] = relationship(back_populates="courses")
    offerings: Mapped[list["CourseOffering"]] = relationship(back_populates="course")


class CourseOffering(Base):
    __tablename__ = "course_offerings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    offering_code: Mapped[str | None] = mapped_column(String)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_years.id"), nullable=False)
    lecturer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lecturers.id"), nullable=False)
    semester: Mapped[str | None] = mapped_column(String)
    day: Mapped[str | None] = mapped_column(String, server_default="Monday")
    start_time: Mapped[str | None] = mapped_column(String)
    end_time: Mapped[str | None] = mapped_column(String)
    venue_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("venues.id"))
    max_students: Mapped[int | None] = mapped_column(SmallInteger)
    late_threshold_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("10"))
    random_check_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    random_check_window_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("10"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    course: Mapped["Course"] = relationship(back_populates="offerings")
    academic_year: Mapped["AcademicYear"] = relationship(back_populates="course_offerings")
    lecturer: Mapped["Lecturer"] = relationship(back_populates="course_offerings")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    venue: Mapped["Venue"] = relationship(back_populates="course_offerings")
    
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="course_offering")
    lecture_sessions: Mapped[list["LectureSession"]] = relationship(back_populates="course_offering")
    chapters: Mapped[list["Chapter"]] = relationship(back_populates="course_offering")
    course_materials: Mapped[list["CourseMaterial"]] = relationship(back_populates="course_offering")
    notices: Mapped[list["Notice"]] = relationship(back_populates="course_offering")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    course_offering_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("course_offerings.id"), nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    enrolled_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    unenrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("enrollments_active_unique", "student_id", "course_offering_id", unique=True, postgresql_where=text("is_active = true")),
    )

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="enrollments")
    course_offering: Mapped["CourseOffering"] = relationship(back_populates="enrollments")
    enroller: Mapped["User"] = relationship(foreign_keys=[enrolled_by])


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    course_offering_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("course_offerings.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    course_offering: Mapped["CourseOffering"] = relationship(back_populates="chapters")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    materials: Mapped[list["CourseMaterial"]] = relationship(back_populates="chapter")


class CourseMaterial(Base):
    __tablename__ = "course_materials"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id"), nullable=False)
    course_offering_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("course_offerings.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer)
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    chapter: Mapped["Chapter"] = relationship(back_populates="materials")
    course_offering: Mapped["CourseOffering"] = relationship(back_populates="course_materials")
    uploader: Mapped["User"] = relationship(foreign_keys=[uploaded_by])


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    course_offering_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("course_offerings.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    urgency: Mapped[NoticeUrgency] = mapped_column(ENUM(NoticeUrgency, name="notice_urgency", create_type=False), nullable=False, server_default="normal")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    target_roles: Mapped[list[UserRole] | None] = mapped_column(PG_ARRAY(ENUM(UserRole, name="user_role", create_type=False)))
    target_user_ids: Mapped[list[uuid.UUID] | None] = mapped_column(PG_ARRAY(Uuid))

    # Relationships
    course_offering: Mapped["CourseOffering"] = relationship(back_populates="notices")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    read_statuses: Mapped[list["NoticeReadStatus"]] = relationship(back_populates="notice")


class NoticeReadStatus(Base):
    __tablename__ = "notice_read_status"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    notice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notices.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    notice: Mapped["Notice"] = relationship(back_populates="read_statuses")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])


class RecordingLink(Base):
    __tablename__ = "recording_links"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    lecture_session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lecture_sessions.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[RecordingPlatform | None] = mapped_column(ENUM(RecordingPlatform, name="recording_platform", create_type=False))
    added_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    upload_date: Mapped[date] = mapped_column(Date, nullable=False)
    upload_time: Mapped[time] = mapped_column(Time, nullable=False)
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    lecture_session: Mapped["LectureSession"] = relationship(back_populates="recording_links")
    adder: Mapped["User"] = relationship(foreign_keys=[added_by])
