from uuid import UUID
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.models.identity import User
from shared_core.schemas.session import LectureSessionOut, SessionCreate
from shared_core.db.session import get_db
from app.services import attendance_service

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.get("", response_model=List[LectureSessionOut])
def list_sessions(offering_id: Optional[UUID] = Query(None), skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return attendance_service.get_sessions(db, offering_id, skip, limit)

@router.post("", response_model=LectureSessionOut, status_code=201)
def start_session(data: SessionCreate, current_user: User = Depends(require_role("lecturer", "admin")), db: Session = Depends(get_db)):
    return attendance_service.start_session(db, data.model_dump(), current_user)

@router.get("/{id}", response_model=LectureSessionOut)
def get_session(id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = attendance_service.get_session(db, id)
    if not session: raise HTTPException(404, "Session not found")
    if getattr(current_user.role, "value", current_user.role) == "student":
        allowed = any(e.student_id == current_user.id and e.is_active for e in session.course_offering.enrollments)
        if not allowed: raise HTTPException(403, "Not enrolled in this session")
    elif getattr(current_user.role, "value", current_user.role) == "lecturer" and session.course_offering.lecturer_id != current_user.id:
        raise HTTPException(403, "Not assigned to this offering")
    return session

@router.post("/{id}/end", response_model=LectureSessionOut)
def end_session(id: UUID, current_user: User = Depends(require_role("lecturer", "admin")), db: Session = Depends(get_db)):
    session = attendance_service.end_session(db, id, current_user)
    if not session: raise HTTPException(404, "Session not found")
    return session

@router.get("/{id}/windows")
def windows(id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return attendance_service.get_active_windows(db, id, current_user.id if getattr(current_user.role,'value',current_user.role)=='student' else None)

@router.get("/{id}/live")
def live(id: UUID, current_user: User = Depends(require_role("lecturer", "admin")), db: Session = Depends(get_db)):
    session = attendance_service.get_session(db, id)
    if not session: raise HTTPException(404, "Session not found")
    if getattr(current_user.role,'value',current_user.role) == 'lecturer' and session.course_offering.lecturer_id != current_user.id:
        raise HTTPException(403, "Not assigned to this offering")
    records = attendance_service.get_student_attendance(db, current_user.id) if False else session.attendance_records
    return {"session_id": id, "status": session.status, "records": [{"student_id": r.student_id, "status": r.status, "first_check_in_at": r.first_check_in_at, "random_check_completed_at": r.random_check_completed_at} for r in records]}
