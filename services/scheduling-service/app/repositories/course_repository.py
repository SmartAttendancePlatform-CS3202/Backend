"""
Data-access layer for courses/offerings. Replace the stub bodies with
real SQLAlchemy queries against the university_attendance_schema.sql
tables (courses, course_offerings, enrollments).
"""
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from shared_core.models.courses import Course

def get_all_courses(db: Session, skip: int = 0, limit: int = 100) -> List[Course]:
    return db.query(Course).offset(skip).limit(limit).all()

def get_course(db: Session, course_id: UUID) -> Optional[Course]:
    return db.query(Course).filter(Course.id == course_id).first()

def create_course(db: Session, course_data: dict) -> Course:
    db_course = Course(**course_data)
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

def update_course(db: Session, course: Course, update_data: dict) -> Course:
    for key, value in update_data.items():
        setattr(course, key, value)
    db.commit()
    db.refresh(course)
    return course
