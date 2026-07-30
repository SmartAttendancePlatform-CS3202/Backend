from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from shared_core.db.session import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.schemas.identity import StudentOut, LecturerOut, UserOut, UserRoleUpdate, StudentUpdate
from shared_core.models.identity import User
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/students/me", response_model=StudentOut)
def get_my_student_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = user_service.get_student(db, current_user.id)
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return student

@router.patch("/students/me", response_model=StudentOut)
def update_my_student_profile(
    update_data: StudentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = user_service.update_student(db, current_user.id, update_data.model_dump(exclude_unset=True))
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return student

@router.get("/lecturers/me", response_model=LecturerOut)
def get_my_lecturer_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    lecturer = user_service.get_lecturer(db, current_user.id)
    if not lecturer:
        raise HTTPException(status_code=404, detail="Lecturer profile not found")
    return lecturer

@router.get("/{id}", response_model=UserOut)
def get_user_by_id(
    id: UUID,
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    user = user_service.get_user(db, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{id}/role", response_model=UserOut)
def update_user_role(
    id: UUID,
    role_data: UserRoleUpdate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    user = user_service.update_user_role(db, id, role_data.model_dump(exclude_unset=True))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
