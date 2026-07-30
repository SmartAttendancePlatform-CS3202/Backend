from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories import enrollment_repository

def create_enrollment(db: Session, student_id: UUID, offering_id: UUID, user_id: UUID):
    return enrollment_repository.create_enrollment(db, student_id, offering_id, user_id)

def get_enrollment(db: Session, enrollment_id: UUID):
    return enrollment_repository.get_enrollment(db, enrollment_id)

def delete_enrollment(db: Session, enrollment_id: UUID):
    enrollment = enrollment_repository.get_enrollment(db, enrollment_id)
    if enrollment:
        enrollment_repository.delete_enrollment(db, enrollment)
        return True
    return False

def get_students_for_offering(db: Session, offering_id: UUID, skip: int = 0, limit: int = 100):
    return enrollment_repository.get_students_for_offering(db, offering_id, skip=skip, limit=limit)
