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
