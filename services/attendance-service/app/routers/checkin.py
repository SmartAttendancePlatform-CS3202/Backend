from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from shared_core.auth.rbac import require_role
from shared_core.models.identity import User
from shared_core.db.session import get_db
from sqlalchemy.orm import Session
from app.services import attendance_service

router = APIRouter(prefix="/checkin", tags=["checkin"])

class CheckInRequest(BaseModel):
    lecture_session_id: UUID
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

class RandomCheckRequest(CheckInRequest):
    verification_window_id: UUID
    face_image_base64: str = Field(min_length=100, max_length=6_800_000)

@router.post("/tick")
def tick(payload: CheckInRequest, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    return attendance_service.record_check_in(db, current_user.id, payload)

@router.post("/random-check", status_code=status.HTTP_202_ACCEPTED)
async def random_check(payload: RandomCheckRequest, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    return await attendance_service.record_random_check(db, current_user.id, payload)

@router.get("/windows/active")
def active_windows(lecture_session_id: UUID, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    return attendance_service.get_active_windows(db, lecture_session_id, current_user.id)
