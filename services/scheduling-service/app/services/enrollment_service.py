from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException
import app.repositories.offering_repository as offering_repository
import app.repositories.user_repository as user_repository
from app.repositories.enrollment_repository import (
    create_enrollment as create_enrollment_record,
    delete_enrollment as delete_enrollment_record,
    get_enrollment as get_enrollment_record,
    get_for_offering as get_for_offering_record,
    get_students_for_offering as get_students_for_offering_record,
)

def create_enrollment(db: Session, student_id: UUID, offering_id: UUID, user_id: UUID):
    student = user_repository.get_student(db, student_id)
    offering = offering_repository.get_offering(db, offering_id)
    if not student or not student.user.is_active or str(student.user.status.value) != "active":
        raise HTTPException(400, "Student is not active")
    if not offering or not offering.is_active:
        raise HTTPException(404, "Offering not found or inactive")
    actor = user_repository.get_user(db, user_id)
    if actor and actor.role.value == "lecturer" and offering.lecturer_id != user_id:
        raise HTTPException(403, "Lecturer is not assigned to this offering")
    current = [e for e in offering.enrollments if e.student_id == student_id and e.is_active]
    if current:
        raise HTTPException(409, "Student is already enrolled")
    if offering.max_students and sum(e.is_active for e in offering.enrollments) >= offering.max_students:
        raise HTTPException(409, "Offering has reached maximum capacity")
    return create_enrollment_record(db, student_id, offering_id, user_id)

def get_enrollment(db: Session, enrollment_id: UUID):
    return get_enrollment_record(db, enrollment_id)

def delete_enrollment(db: Session, enrollment_id: UUID, user_id: UUID):
    enrollment = get_enrollment_record(db, enrollment_id)
    if not enrollment: return False
    if getattr(enrollment.course_offering.lecturer_id, "hex", None) and enrollment.course_offering.lecturer_id != user_id:
        # Admin ownership is handled at router level; lecturer must own offering.
        actor = user_repository.get_user(db, user_id)
        if not actor or actor.role.value != "admin": raise HTTPException(403, "Forbidden")
    delete_enrollment_record(db, enrollment)
    return True

def get_students_for_offering(db: Session, offering_id: UUID, skip: int = 0, limit: int = 100):
    return get_students_for_offering_record(db, offering_id, skip=skip, limit=limit)


def get_for_offering(db, offering_id): return get_for_offering_record(db, offering_id)
