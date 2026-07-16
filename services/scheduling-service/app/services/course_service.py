"""
Business logic for courses and offerings. Talks to the repository
layer, not the database directly — keeps routers thin and this layer
testable without a live DB.
"""
from uuid import UUID

from app.repositories import course_repository


def list_courses():
    return course_repository.list_all()


def create_course(course):
    return course_repository.create(course)


def list_offerings(course_id: UUID):
    return course_repository.list_offerings_for_course(course_id)


def get_timetable_for_student(student_id: str):
    return course_repository.list_offerings_for_student(student_id)
