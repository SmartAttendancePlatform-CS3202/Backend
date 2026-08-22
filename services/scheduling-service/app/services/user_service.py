from uuid import UUID
from typing import List
from sqlalchemy.orm import Session
from app.repositories import user_repository

def get_user(db: Session, user_id: UUID):
    return user_repository.get_user(db, user_id=user_id)

def get_student(db: Session, student_id: UUID):
    return user_repository.get_student(db, student_id=student_id)

def get_lecturer(db: Session, lecturer_id: UUID):
    return user_repository.get_lecturer(db, lecturer_id=lecturer_id)

def get_all_users(db: Session, role: str = None, status: str = None, skip: int = 0, limit: int = 100):
    return user_repository.get_all_users(db, role=role, status=status, skip=skip, limit=limit)

def get_all_lecturers(db: Session, skip: int = 0, limit: int = 100):
    return user_repository.get_all_lecturers(db, skip=skip, limit=limit)

def get_all_students(db: Session, skip: int = 0, limit: int = 100):
    return user_repository.get_all_students(db, skip=skip, limit=limit)

def update_user_role(db: Session, user_id: UUID, role_data: dict):
    user = user_repository.get_user(db, user_id=user_id)
    if not user:
        return None
    return user_repository.update_user(db, user=user, update_data=role_data)

def update_student(db: Session, student_id: UUID, update_data: dict):
    student = user_repository.get_student(db, student_id=student_id)
    if not student:
        return None
    return user_repository.update_student(db, student=student, update_data=update_data)



def update_user_status(db: Session, user_id: UUID, status: str):
    user = user_repository.get_user(db, user_id)
    if not user: return None
    return user_repository.update_user(db, user=user, update_data={"status": status, "is_active": status == "active"})
