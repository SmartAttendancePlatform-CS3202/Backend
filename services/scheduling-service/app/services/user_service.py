from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
import app.repositories.user_repository as user_repository

def get_user(db: Session, user_id: UUID):
    return user_repository.get_user(db, user_id=user_id)

def get_student(db: Session, student_id: UUID):
    return user_repository.get_student(db, student_id=student_id)

def get_lecturer(db: Session, lecturer_id: UUID):
    return user_repository.get_lecturer(db, lecturer_id=lecturer_id)

def get_all_users(db: Session, role: Optional[str] = None, status: Optional[str] = None, skip: int = 0, limit: int = 100):
    return user_repository.get_all_users(db, role=role, status=status, skip=skip, limit=limit)

def get_all_lecturers(db: Session, skip: int = 0, limit: int = 100):
    return user_repository.get_all_lecturers(db, skip=skip, limit=limit)

def get_all_students(db: Session, skip: int = 0, limit: int = 100):
    return user_repository.get_all_students(db, skip=skip, limit=limit)

def update_user_role(db: Session, user_id: UUID, role_data: dict):
    user = user_repository.get_user(db, user_id=user_id)
    if not user:
        return None
    profile_data = {}
    if "display_name" in role_data:
        profile_data["display_name"] = role_data.pop("display_name")
    if "department_id" in role_data:
        profile_data["department_id"] = role_data.pop("department_id")
    if "identifier" in role_data:
        profile_data["identifier"] = role_data.pop("identifier")
    updated = user_repository.update_user(db, user=user, update_data=role_data)
    if profile_data:
        role = getattr(updated.role, "value", updated.role)
        if role == "student" and updated.student_profile:
            if "display_name" in profile_data: updated.student_profile.display_name = profile_data["display_name"]
            if "department_id" in profile_data: updated.student_profile.department_id = profile_data["department_id"]
            if "identifier" in profile_data: updated.student_profile.student_index_no = profile_data["identifier"]
        elif role == "lecturer" and updated.lecturer_profile:
            if "department_id" in profile_data: updated.lecturer_profile.department_id = profile_data["department_id"]
            if "identifier" in profile_data: updated.lecturer_profile.lecturer_code = profile_data["identifier"]
        db.commit(); db.refresh(updated)
    return updated

def update_student(db: Session, student_id: UUID, update_data: dict):
    student = user_repository.get_student(db, student_id=student_id)
    if not student:
        return None
    return user_repository.update_student(db, student=student, update_data=update_data)



def update_user_status(db: Session, user_id: UUID, status: str):
    user = user_repository.get_user(db, user_id)
    if not user: return None
    return user_repository.update_user(db, user=user, update_data={"status": status, "is_active": status == "active"})
