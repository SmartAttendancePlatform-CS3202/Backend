from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from shared_core.db.session import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.models.identity import User
from pydantic import BaseModel
from typing import Optional

from app.services import attendance_service

router = APIRouter(prefix="/checkin", tags=["checkin"])

class CheckInRequest(BaseModel):
    lecture_session_id: UUID
    latitude: float
    longitude: float

class RandomCheckRequest(CheckInRequest):
    verification_window_id: UUID
    face_image_base64: str

@router.post("/tick")
def record_check_in_tick(
    payload: CheckInRequest,
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db)
):
    try:
        return attendance_service.record_check_in(db, current_user.id, payload)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/random-check", status_code=status.HTTP_202_ACCEPTED)
async def record_random_check(
    payload: RandomCheckRequest,
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db)
):
    return await attendance_service.record_random_check(db, current_user.id, payload)

@router.get("/windows/active")
def get_active_windows(
    lecture_session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return attendance_service.get_active_windows(db, lecture_session_id)
