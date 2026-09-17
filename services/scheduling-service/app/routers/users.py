from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional

from shared_core.db.session import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.schemas.identity import StudentOut, LecturerOut, UserOut, UserRoleUpdate, StudentUpdate, UserDirectoryOut, StudentRegistrationRequest
from shared_core.models.identity import User
from shared_core.models.enums import UserRole, UserStatus

from shared_core.audit import audit

try:
    import app.services.user_service as user_service
except ImportError:  # pragma: no cover
    from app.services import user_service  # type: ignore[reportAttributeAccessIssue]

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/register", response_model=UserOut)
def register_student_user(
    data: StudentRegistrationRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    try:
        user = user_service.register_student(db, data, current_user.id)
        audit(db, current_user.id, "user.register", "user", user.id, new_data={"email": data.email, "role": "student"})
        return user
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))

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
        payload.update({
            "student_index_no": p.student_index_no,
            "full_name": p.full_name,
            "name_with_initials": p.name_with_initials,
            "display_name": p.display_name,
            "department_id": p.department_id,
            "academic_year_id": p.academic_year_id,
            "photo_url": p.photo_url,
            "department_name": p.department.name if p.department else None,
            "department_code": p.department.code if p.department else None,
            "faculty_name": p.department.faculty_name if p.department else None,
            "faculty_head": p.department.faculty_head if p.department else None,
            "academic_year_name": p.academic_year.name if p.academic_year else None,
            "academic_year_level": p.academic_year.year_level if p.academic_year else None,
            "gender": getattr(p.gender, "value", p.gender) if hasattr(p, "gender") and p.gender else None,
            "date_of_birth": str(p.date_of_birth) if p.date_of_birth else None,
            "nic": p.nic,
            "contact_number": p.contact_number,
            "address": p.address,
        })
    return payload

@router.get("", response_model=List[UserOut])
def list_users(
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
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
    updated_user = user_service.update_user_status(db, id, "active")
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    audit(db, current_user.id, "user.approve", "user", updated_user.id, new_data={"status": "active"})
    db.commit()
    return updated_user

@router.post("/{id}/reject", response_model=UserOut)
def reject_user(id: UUID, current_user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    user = user_service.get_user(db, id)
    if not user: raise HTTPException(404, "User not found")
    updated_user = user_service.update_user_status(db, id, "inactive")
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    audit(db, current_user.id, "user.reject", "user", updated_user.id, new_data={"status": "inactive"})
    db.commit()
    return updated_user

@router.get("/lecturers", response_model=List[LecturerOut])
def list_lecturers(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    """Admin user directory: flattened list of accounts + their student/lecturer
    profile fields, with optional role/status filters. Backs the web dashboard's
    Admin > Users page."""
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
    updated_user = user_service.update_user_role(db, id, role_data.model_dump(exclude_unset=True))
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    audit(
        db,
        current_user.id,
        "user.role_or_status.update",
        "user",
        updated_user.id,
        old_data=old,
        new_data={"role": getattr(updated_user.role, "value", updated_user.role), "status": getattr(updated_user.status, "value", updated_user.status)},
    )
    db.commit()
    return updated_user
