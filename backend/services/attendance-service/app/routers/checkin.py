from fastapi import APIRouter, Depends

from shared_core.auth.jwt import get_current_user
from shared_core.schemas.session import CheckInRequest, RandomCheckRequest

from app.services import attendance_service

router = APIRouter(prefix="/checkin", tags=["checkin"])


@router.post("/tick")
def check_in_tick(payload: CheckInRequest, user: dict = Depends(get_current_user)):
    """The start-of-lecture tick: location only, no face verification."""
    return attendance_service.record_check_in(student_id=user["sub"], payload=payload)


@router.post("/random-check")
def random_check(payload: RandomCheckRequest, user: dict = Depends(get_current_user)):
    """The mid-lecture window: requires both face verification (delegated
    to ai-vision-service) and a location check together."""
    return attendance_service.record_random_check(student_id=user["sub"], payload=payload)
