from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional

from shared_core.db.session import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.schemas.identity import StudentOut, LecturerOut, UserOut, UserRoleUpdate, StudentUpdate
from shared_core.models.identity import User
from app.services import user_service
from shared_core.audit import audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payload = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.username,
        "role": getattr(current_user.role, "value", current_user.role),
        "status": getattr(current_user.status, "value", current_user.status),
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }
    if getattr(current_user.role, "value", current_user.role) == "lecturer" and current_user.lecturer_profile:
        p = current_user.lecturer_profile
        payload.update({"lecturer_code": p.lecturer_code, "display_name": p.display_name if hasattr(p, "display_name") else p.email, "email": p.email or current_user.username, "department_id": p.department_id})
    elif getattr(current_user.role, "value", current_user.role) == "student" and current_user.student_profile:
        p = current_user.student_profile
        payload.update({"student_index_no": p.student_index_no, "full_name": p.full_name, "name_with_initials": p.name_with_initials, "display_name": p.display_name, "department_id": p.department_id, "academic_year_id": p.academic_year_id, "photo_url": p.photo_url})
    return payload

@router.get("", response_model=List[UserOut])
def list_users(
    role: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    return user_service.get_all_users(db, role=role, status=status, skip=skip, limit=limit)


@router.get("/pending", response_model=List[UserOut])
def pending_users(skip: int = 0, limit: int = 100, current_user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return user_service.get_all_users(db, status="pending_approval", skip=skip, limit=limit)

@router.post("/{id}/approve", response_model=UserOut)
def approve_user(id: UUID, current_user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    user = user_service.get_user(db, id)
    if not user: raise HTTPException(404, "User not found")
    user = user_service.update_user_status(db, id, "active")
    audit(db, current_user.id, "user.approve", "user", user.id, new_data={"status": "active"})
    db.commit()
    return user

@router.post("/{id}/reject", response_model=UserOut)
def reject_user(id: UUID, current_user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    user = user_service.get_user(db, id)
    if not user: raise HTTPException(404, "User not found")
    user = user_service.update_user_status(db, id, "inactive")
    audit(db, current_user.id, "user.reject", "user", user.id, new_data={"status": "inactive"})
    db.commit()
    return user

@router.get("/lecturers", response_model=List[LecturerOut])
def list_lecturers(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    return user_service.get_all_lecturers(db, skip=skip, limit=limit)

@router.get("/students", response_model=List[StudentOut])
def list_students(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    return user_service.get_all_students(db, skip=skip, limit=limit)


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
    user = user_service.get_user(db, id)
    if not user: raise HTTPException(status_code=404, detail="User not found")
    old = {"role": getattr(user.role,"value",user.role), "status": getattr(user.status,"value",user.status)}
    user = user_service.update_user_role(db, id, role_data.model_dump(exclude_unset=True))
    audit(db, current_user.id, "user.role_or_status.update", "user", user.id, old_data=old, new_data={"role": getattr(user.role,"value",user.role), "status": getattr(user.status,"value",user.status)})
    db.commit()
    return user
