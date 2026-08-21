from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from shared_core.models.identity import User, Student, Lecturer

def get_user(db: Session, user_id: UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_student(db: Session, student_id: UUID) -> Optional[Student]:
    return db.query(Student).filter(Student.id == student_id).first()

def get_lecturer(db: Session, lecturer_id: UUID) -> Optional[Lecturer]:
    return db.query(Lecturer).filter(Lecturer.id == lecturer_id).first()

def get_all_users(db: Session, role: Optional[str] = None, status: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[User]:
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    return query.offset(skip).limit(limit).all()

def get_all_lecturers(db: Session, skip: int = 0, limit: int = 100) -> List[Lecturer]:
    return db.query(Lecturer).offset(skip).limit(limit).all()

def get_all_students(db: Session, skip: int = 0, limit: int = 100) -> List[Student]:
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

