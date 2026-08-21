import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .courses import Course, CourseOffering, Enrollment
    from .attendance import AttendanceVerificationAttempt, AttendanceRecord
    from .vision import FaceProfile
from sqlalchemy import String, Boolean, DateTime, func, ForeignKey, SmallInteger, Text, text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ENUM

from .base import Base
from .enums import UserRole, UserStatus, GenderType


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str | None] = mapped_column(String)
    faculty_head: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    faculty_name: Mapped[str | None] = mapped_column(String)
    contact_number: Mapped[str | None] = mapped_column(String)

    # Relationships
    students: Mapped[list["Student"]] = relationship(back_populates="department")
    lecturers: Mapped[list["Lecturer"]] = relationship(back_populates="department")
    courses: Mapped[list["Course"]] = relationship(back_populates="department")


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    year_level: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)

    # Relationships
    students: Mapped[list["Student"]] = relationship(back_populates="academic_year")
    course_offerings: Mapped[list["CourseOffering"]] = relationship(back_populates="academic_year")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(ENUM(UserRole, name="user_role", create_type=False), nullable=False)
    status: Mapped[UserStatus] = mapped_column(ENUM(UserStatus, name="user_status", create_type=False), nullable=False, server_default="pending_approval")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    student_profile: Mapped["Student"] = relationship(back_populates="user", uselist=False, foreign_keys="Student.id")
    lecturer_profile: Mapped["Lecturer"] = relationship(back_populates="user", uselist=False, foreign_keys="Lecturer.id")
    registered_students: Mapped[list["Student"]] = relationship(back_populates="registrar", foreign_keys="Student.registered_by")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    student_index_no: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    name_with_initials: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id"), nullable=False)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_years.id"), nullable=False)
    date_of_birth: Mapped[datetime] = mapped_column(Date, nullable=False)
    gender: Mapped[GenderType] = mapped_column(ENUM(GenderType, name="gender_type", create_type=False), nullable=False)
    nic: Mapped[str | None] = mapped_column(String, unique=True)
    contact_number: Mapped[str | None] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)
    registered_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="student_profile", foreign_keys=[id])
    department: Mapped["Department"] = relationship(back_populates="students")
    academic_year: Mapped["AcademicYear"] = relationship(back_populates="students")
    registrar: Mapped["User"] = relationship(back_populates="registered_students", foreign_keys=[registered_by])
    
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")
    face_profile: Mapped["FaceProfile"] = relationship(back_populates="student", uselist=False)
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(back_populates="student")
    verification_attempts: Mapped[list["AttendanceVerificationAttempt"]] = relationship(back_populates="student")


class Lecturer(Base):
    __tablename__ = "lecturers"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    lecturer_code: Mapped[str | None] = mapped_column(String, unique=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id"))
    contact_number: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    photo_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="lecturer_profile", foreign_keys=[id])
    department: Mapped["Department"] = relationship(back_populates="lecturers")
    course_offerings: Mapped[list["CourseOffering"]] = relationship(back_populates="lecturer")
