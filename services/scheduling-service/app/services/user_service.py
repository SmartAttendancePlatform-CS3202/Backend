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

import httpx
from shared_core.config import get_settings
from fastapi import HTTPException
from shared_core.schemas.identity import StudentRegistrationRequest

from shared_core.schemas.identity import StudentRegistrationRequest, LecturerRegistrationRequest, AdminRegistrationRequest
from typing import Union

def register_user(db: Session, data: Union[StudentRegistrationRequest, LecturerRegistrationRequest, AdminRegistrationRequest], current_user_id: UUID):
    settings = get_settings()
    # 1. Create user in Supabase
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": data.email,
        "password": data.password,
        "email_confirm": True,
        "user_metadata": {
            "role": data.role,
            "username": data.email.split('@')[0],
        },
    }
    res = httpx.post(
        f"{settings.supabase_url}/auth/v1/admin/users",
        headers=headers,
        json=payload,
    )
    if res.status_code not in (200, 201):
        raise HTTPException(status_code=res.status_code, detail=res.json().get("message", "Failed to create user in Supabase"))
    
    supabase_user = res.json()
    new_user_id = UUID(supabase_user["id"])

    # 2. Create User in Postgres
    user_data = {
        "id": new_user_id,
        "username": data.email,
        "role": data.role,
        "status": "active",
        "is_active": True,
        "must_change_password": False,
    }
    
    # Supabase might have an auth trigger that auto-creates the public.users row.
    existing_user = user_repository.get_user(db, new_user_id)
    if existing_user:
        user_repository.update_user(db, existing_user, {"role": data.role, "status": "active", "is_active": True})
    else:
        user_repository.create_user(db, user_data)

    # 3. Create Profile in Postgres
    if data.role == "student":
        student_data = {
            "id": new_user_id,
            "student_index_no": getattr(data, "student_index_no", None),
            "full_name": getattr(data, "full_name", None),
            "name_with_initials": getattr(data, "name_with_initials", None),
            "display_name": getattr(data, "display_name", None),
            "department_id": getattr(data, "department_id", None),
            "academic_year_id": getattr(data, "academic_year_id", None),
            "date_of_birth": getattr(data, "date_of_birth", None),
            "gender": getattr(data, "gender", None),
            "nic": getattr(data, "nic", None),
            "contact_number": getattr(data, "contact_number", None),
            "address": getattr(data, "address", None),
            "registered_by": current_user_id
        }
        user_repository.create_student(db, student_data)
    elif data.role == "lecturer":
        lecturer_data = {
            "id": new_user_id,
            "lecturer_code": getattr(data, "employee_id", None),
            "display_name": getattr(data, "display_name", getattr(data, "full_name", None)),
            "department_id": getattr(data, "department_id", None),
            "email": data.email,
            "contact_number": getattr(data, "contact_number", None),
        }
        user_repository.create_lecturer(db, lecturer_data)
    
    return user_repository.get_user(db, new_user_id)
