from uuid import UUID, uuid4
from typing import List, Optional
from datetime import datetime, timezone, timedelta
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
    face_embedding: List[float] = Field(
        ...,
        min_length=192,
        max_length=192,
        description="192-dimensional MobileFaceNet embedding vector",
    )


class RandomCheckRequest(BaseModel):
    lecture_session_id: UUID
    verification_window_id: UUID
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    face_embedding: List[float] = Field(
        ...,
        min_length=192,
        max_length=192,
        description="192-dimensional MobileFaceNet embedding vector",
    )


class VerifyLocationRequest(BaseModel):
    lecture_session_id: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class VerifyFaceRequest(BaseModel):
    lecture_session_id: Optional[str] = None
    verification_window_id: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    face_embedding: List[float] = Field(
        ...,
        min_length=192,
        max_length=192,
        description="192-dimensional MobileFaceNet embedding vector",
    )
    depth_features: Optional[List[float]] = None


@router.post("/verify-location", status_code=status.HTTP_200_OK)
def verify_location(
    payload: VerifyLocationRequest,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    return attendance_service.verify_location_precheck(db, current_user.id, payload)


@router.post("/verify-face", status_code=status.HTTP_200_OK)
def verify_face(
    payload: VerifyFaceRequest,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    return attendance_service.verify_face_and_record_attendance(db, current_user.id, payload)


@router.post("/tick", status_code=status.HTTP_202_ACCEPTED)
async def tick(
    payload: CheckInRequest,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    return await attendance_service.record_check_in(db, current_user.id, payload)


@router.post("/random-check", status_code=status.HTTP_202_ACCEPTED)
async def random_check(
    payload: RandomCheckRequest,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    return await attendance_service.record_random_check(db, current_user.id, payload)


@router.get("/windows/active")
def active_windows(
    lecture_session_id: str,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    if lecture_session_id == "TEST_MOCK_CLASS":
        now = datetime.now(timezone.utc)
        return {
            "check_in_window": {
                "id": str(uuid4()),
                "window_type": "check_in",
                "is_active": True,
                "opened_at": now.isoformat(),
                "closed_at": (now + timedelta(hours=1)).isoformat(),
            },
            "random_check_active": False,
            "random_check_window": None,
            "venue_geofence": {
                "venue_name": "Anywhere (Testing & Debugging)",
                "building": "Virtual / Testing Mode",
                "latitude": 0.0,
                "longitude": 0.0,
                "radius_meters": 999999,
            },
        }
    try:
        session_uuid = UUID(lecture_session_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid lecture session ID format")
    return attendance_service.get_active_windows(db, session_uuid, current_user.id)


