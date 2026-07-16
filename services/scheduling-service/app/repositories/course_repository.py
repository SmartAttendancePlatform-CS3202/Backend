"""
Data-access layer for courses/offerings. Replace the stub bodies with
real SQLAlchemy queries against the university_attendance_schema.sql
tables (courses, course_offerings, enrollments).
"""
from uuid import UUID


def list_all():
    raise NotImplementedError


def create(course):
    raise NotImplementedError


def list_offerings_for_course(course_id: UUID):
    raise NotImplementedError


def list_offerings_for_student(student_id: str):
    raise NotImplementedError
