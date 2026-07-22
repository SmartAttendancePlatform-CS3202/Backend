from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories import offering_repository

def get_timetable_for_student(db: Session, student_id: UUID):
    return offering_repository.get_offerings_for_student(db, student_id)

def get_timetable_for_lecturer(db: Session, lecturer_id: UUID):
    return offering_repository.get_offerings_for_lecturer(db, lecturer_id)
