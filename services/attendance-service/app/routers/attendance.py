from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from shared_core.database.connection import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.models.identity import User
from shared_core.schemas.session import AttendanceRecordOut, AttemptOut
from app.services import attendance_service

router = APIRouter(prefix="/attendance", tags=["attendance"])

@router.get("/me", response_model=List[AttendanceRecordOut])
def get_my_attendance(
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db)
):
    return attendance_service.get_student_attendance(db, current_user.id)

@router.get("/students/{id}", response_model=List[AttendanceRecordOut])
def get_student_attendance(
    id: UUID,
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    return attendance_service.get_student_attendance(db, id)

@router.patch("/records/{id}/override", response_model=AttendanceRecordOut)
def override_attendance_record(
    id: UUID,
    override_data: dict, # Could define a specific schema for this
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    record = attendance_service.override_record(db, id, current_user.id, override_data)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    return record

@router.get("/records/{id}/attempts", response_model=List[AttemptOut])
def get_attendance_attempts(
    id: UUID,
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    return attendance_service.get_attendance_attempts(db, id)
