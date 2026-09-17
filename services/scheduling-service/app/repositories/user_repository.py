from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from shared_core.models.identity import User, Student, Lecturer
from shared_core.models.enums import UserRole, UserStatus

def get_user(db: Session, user_id: UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_all_users(
    db: Session,
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[User]:
    """List users with their student/lecturer profile + department eager-loaded,
    so the service layer can flatten them without extra queries per row."""
    query = db.query(User).options(
        joinedload(User.student_profile).joinedload(Student.department),
        joinedload(User.lecturer_profile).joinedload(Lecturer.department),
    )
    if role is not None:
        query = query.filter(User.role == role)
    if status is not None:
        query = query.filter(User.status == status)
    return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

def get_student(db: Session, student_id: UUID) -> Optional[Student]:
    return db.query(Student).filter(Student.id == student_id).first()

def get_lecturer(db: Session, lecturer_id: UUID) -> Optional[Lecturer]:
    return db.query(Lecturer).filter(Lecturer.id == lecturer_id).first()

def get_all_lecturers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Lecturer).offset(skip).limit(limit).all()

def get_all_students(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Student).offset(skip).limit(limit).all()

def update_user(db: Session, user: User, update_data: dict) -> User:
    for key, value in update_data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user

def update_student(db: Session, student: Student, update_data: dict) -> Student:
    for key, value in update_data.items():
        setattr(student, key, value)
    db.commit()
    db.refresh(student)
    return student

def create_user(db: Session, user_data: dict) -> User:
    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_student(db: Session, student_data: dict) -> Student:
    student = Student(**student_data)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student