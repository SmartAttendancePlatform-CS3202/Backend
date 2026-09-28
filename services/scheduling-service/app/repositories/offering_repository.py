from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload, selectinload
from shared_core.models.courses import CourseOffering, Enrollment
from shared_core.models.identity import Lecturer

def get_all_offerings(db: Session, skip: int = 0, limit: int = 100) -> List[CourseOffering]:
    return (
        db.query(CourseOffering)
        .options(
            joinedload(CourseOffering.course),
            joinedload(CourseOffering.academic_year),
            joinedload(CourseOffering.venue),
            joinedload(CourseOffering.lecturer).joinedload(Lecturer.user),
            selectinload(CourseOffering.enrollments)
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_offering(db: Session, offering_id: UUID) -> Optional[CourseOffering]:
    return (
        db.query(CourseOffering)
        .options(
            joinedload(CourseOffering.course),
            joinedload(CourseOffering.academic_year),
            joinedload(CourseOffering.venue),
            joinedload(CourseOffering.lecturer).joinedload(Lecturer.user),
            selectinload(CourseOffering.enrollments)
        )
        .filter(CourseOffering.id == offering_id)
        .first()
    )

def get_offerings_by_course(db: Session, course_id: UUID, skip: int = 0, limit: int = 100) -> List[CourseOffering]:
    return db.query(CourseOffering).filter(CourseOffering.course_id == course_id).offset(skip).limit(limit).all()

def create_offering(db: Session, data: dict, user_id: UUID) -> CourseOffering:
    data['created_by'] = user_id
    db_obj = CourseOffering(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_offering(db: Session, db_obj: CourseOffering, update_data: dict) -> CourseOffering:
    for key, value in update_data.items():
        setattr(db_obj, key, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_offerings_for_student(db: Session, student_id: UUID) -> List[CourseOffering]:
    return (
        db.query(CourseOffering)
        .join(Enrollment, CourseOffering.id == Enrollment.course_offering_id)
        .options(
            joinedload(CourseOffering.course),
            joinedload(CourseOffering.academic_year),
            joinedload(CourseOffering.venue),
            joinedload(CourseOffering.lecturer).joinedload(Lecturer.user),
            selectinload(CourseOffering.enrollments)
        )
        .filter(Enrollment.student_id == student_id, Enrollment.is_active == True)
        .all()
    )

def get_offerings_for_lecturer(db: Session, lecturer_id: UUID) -> List[CourseOffering]:
    return (
        db.query(CourseOffering)
        .options(
            joinedload(CourseOffering.course),
            joinedload(CourseOffering.academic_year),
            joinedload(CourseOffering.venue),
            joinedload(CourseOffering.lecturer).joinedload(Lecturer.user),
            selectinload(CourseOffering.enrollments)
        )
        .filter(CourseOffering.lecturer_id == lecturer_id, CourseOffering.is_active == True)
        .all()
    )
