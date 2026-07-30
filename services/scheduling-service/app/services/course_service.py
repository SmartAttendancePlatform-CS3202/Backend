"""
Business logic for courses and offerings. Talks to the repository
layer, not the database directly — keeps routers thin and this layer
testable without a live DB.
"""
from uuid import UUID
from typing import List
from sqlalchemy.orm import Session
from app.repositories import course_repository

def get_all_courses(db: Session, skip: int = 0, limit: int = 100):
    return course_repository.get_all_courses(db, skip=skip, limit=limit)

def get_course(db: Session, course_id: UUID):
    return course_repository.get_course(db, course_id=course_id)

def create_course(db: Session, course_data: dict):
    return course_repository.create_course(db, course_data=course_data)

def update_course(db: Session, course_id: UUID, update_data: dict):
    course = course_repository.get_course(db, course_id=course_id)
    if not course:
        return None
    return course_repository.update_course(db, course=course, update_data=update_data)
