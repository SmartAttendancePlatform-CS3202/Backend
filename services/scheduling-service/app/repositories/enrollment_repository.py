from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from shared_core.models.courses import Enrollment, CourseOffering
from shared_core.models.identity import Student
from datetime import datetime

def create_enrollment(db: Session, student_id: UUID, offering_id: UUID, user_id: UUID) -> Enrollment:
    db_obj = Enrollment(
        student_id=student_id,
        course_offering_id=offering_id,
        enrolled_by=user_id
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_enrollment(db: Session, enrollment_id: UUID) -> Optional[Enrollment]:
    return db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()

def delete_enrollment(db: Session, db_obj: Enrollment):
    db_obj.is_active = False
    db_obj.unenrolled_at = datetime.utcnow()
    db.commit()

def get_students_for_offering(db: Session, offering_id: UUID, skip: int = 0, limit: int = 100) -> List[Student]:
    return (
        db.query(Student)
        .join(Enrollment, Student.id == Enrollment.student_id)
        .filter(Enrollment.course_offering_id == offering_id, Enrollment.is_active == True)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_for_offering(db, offering_id):
    return db.query(Enrollment).filter(Enrollment.course_offering_id == offering_id).order_by(Enrollment.enrolled_at.desc()).all()
