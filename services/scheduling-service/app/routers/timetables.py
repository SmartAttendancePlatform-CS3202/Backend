from fastapi import APIRouter, Depends

from shared_core.auth.jwt import get_current_user

from app.services import course_service

router = APIRouter(prefix="/timetables", tags=["timetables"])


@router.get("/me")
def my_timetable(user: dict = Depends(get_current_user)):
    """Returns the caller's enrolled course offerings and lecture schedule."""
    return course_service.get_timetable_for_student(user["sub"])
