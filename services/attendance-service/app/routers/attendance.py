from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from shared_core.db.session import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.models.identity import User
from shared_core.schemas.session import AttendanceRecordOut, AttemptOut, AttendanceOverrideRequest
from app.services import attendance_service

router = APIRouter(prefix="/attendance", tags=["attendance"])

@router.get("/records", response_model=List[AttendanceRecordOut])
def records(session_id: Optional[UUID] = Query(None), student_id: Optional[UUID] = Query(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role = getattr(current_user.role, "value", current_user.role)
    if role == "student":
        if student_id and student_id != current_user.id:
            raise HTTPException(403, "Forbidden")
        return attendance_service.get_records(db, session_id=session_id, student_id=current_user.id)
    if role == "lecturer" and session_id:
        session = attendance_service.get_session(db, session_id)
        if not session or session.course_offering.lecturer_id != current_user.id:
            raise HTTPException(403, "Forbidden")
    if role == "lecturer" and student_id:
        # Only records from the lecturer's offerings are returned.
        return [r for r in attendance_service.get_records(db, student_id=student_id) if r.lecture_session.course_offering.lecturer_id == current_user.id]
    return attendance_service.get_records(db, session_id=session_id, student_id=student_id)

@router.get("/me", response_model=List[AttendanceRecordOut])
def me(current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    return attendance_service.get_student_attendance(db, current_user.id)

@router.get("/students/{id}", response_model=List[AttendanceRecordOut])
def student(id: UUID, current_user: User = Depends(require_role("admin", "lecturer")), db: Session = Depends(get_db)):
    return attendance_service.get_student_attendance(db, id)

@router.get("/records/{id}", response_model=AttendanceRecordOut)
def record(id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = db.get(__import__('shared_core.models.attendance', fromlist=['AttendanceRecord']).AttendanceRecord, id)
    if not obj: raise HTTPException(404, "Attendance record not found")
    role = getattr(current_user.role,'value',current_user.role)
    if role == 'student' and obj.student_id != current_user.id: raise HTTPException(403, "Forbidden")
    if role == 'lecturer' and obj.lecture_session.course_offering.lecturer_id != current_user.id: raise HTTPException(403, "Forbidden")
    return obj

@router.patch("/records/{id}/override", response_model=AttendanceRecordOut)
def override(id: UUID, data: AttendanceOverrideRequest = Body(...), current_user: User = Depends(require_role("admin", "lecturer")), db: Session = Depends(get_db)):
    obj = db.get(__import__('shared_core.models.attendance', fromlist=['AttendanceRecord']).AttendanceRecord, id)
    if not obj: raise HTTPException(404, "Attendance record not found")
    if getattr(current_user.role,'value',current_user.role) == 'lecturer' and obj.lecture_session.course_offering.lecturer_id != current_user.id: raise HTTPException(403, "Forbidden")
    if not data.override_reason: raise HTTPException(400, "override_reason is required")
    return attendance_service.override_record(db, id, current_user.id, data.model_dump(exclude_unset=True))

@router.get("/records/{id}/attempts", response_model=List[AttemptOut])
def attempts(id: UUID, current_user: User = Depends(require_role("admin", "lecturer")), db: Session = Depends(get_db)):
    return attendance_service.get_attendance_attempts(db, id)

@router.get("/attempts", response_model=List[AttemptOut])
def recent(offering_id: Optional[UUID] = Query(None), current_user: User = Depends(require_role("admin", "lecturer")), db: Session = Depends(get_db)):
    return attendance_service.get_recent_attempts(db, offering_id)
