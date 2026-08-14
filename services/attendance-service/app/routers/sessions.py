from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from shared_core.db.session import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.models.identity import User
from shared_core.schemas.session import LectureSessionOut, SessionCreate
from app.services import attendance_service
from promethes_client import Gauge

router = APIRouter(prefix="/sessions", tags=["sessions"])

Active_SESSIONS = Gauge(
    "active_sessions",
    "Number of active lecture sessions"
)

@router.get("", response_model=List[LectureSessionOut])
def list_sessions(
    offering_id: UUID = None,
    skip: int = 0, limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return attendance_service.get_sessions(db, offering_id=offering_id, skip=skip, limit=limit)

@router.post("", response_model=LectureSessionOut, status_code=status.HTTP_201_CREATED)
def start_session(
    data: SessionCreate,
    current_user: User = Depends(require_role(["lecturer", "admin"])),
    db: Session = Depends(get_db)
):
    ACTIVE_SESSIONS.inc()
    return attendance_service.start_session(db, data.model_dump())

@router.get("/{id}", response_model=LectureSessionOut)
def get_session(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = attendance_service.get_session(db, id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/{id}/end", response_model=LectureSessionOut)
def end_session(
    id: UUID,
    current_user: User = Depends(require_role(["lecturer", "admin"])),
    db: Session = Depends(get_db)
):
    session = attendance_service.end_session(db, id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    ACTIVE_SESSIONS.dec()
    return session

@router.get("/{id}/live")
def get_session_live_status(
    id: UUID,
    current_user: User = Depends(require_role(["lecturer", "admin"])),
    db: Session = Depends(get_db)
):
    windows = attendance_service.get_active_windows(db, id)
    return windows
