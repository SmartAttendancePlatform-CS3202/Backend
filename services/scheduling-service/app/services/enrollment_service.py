from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.repositories import enrollment_repository, offering_repository, user_repository

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
    return enrollment_repository.create_enrollment(db, student_id, offering_id, user_id)

def get_enrollment(db: Session, enrollment_id: UUID):
    return enrollment_repository.get_enrollment(db, enrollment_id)

def delete_enrollment(db: Session, enrollment_id: UUID, user_id: UUID):
    enrollment = enrollment_repository.get_enrollment(db, enrollment_id)
    if not enrollment: return False
    if getattr(enrollment.course_offering.lecturer_id, "hex", None) and enrollment.course_offering.lecturer_id != user_id:
        # Admin ownership is handled at router level; lecturer must own offering.
        from shared_core.models.identity import User
        actor = user_repository.get_user(db, user_id)
        if not actor or actor.role.value != "admin": raise HTTPException(403, "Forbidden")
    enrollment_repository.delete_enrollment(db, enrollment)
    return True

def get_students_for_offering(db: Session, offering_id: UUID, skip: int = 0, limit: int = 100):
    return enrollment_repository.get_students_for_offering(db, offering_id, skip=skip, limit=limit)
