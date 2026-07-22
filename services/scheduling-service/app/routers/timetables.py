from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from shared_core.database.connection import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.schemas.course import CourseOfferingOut
from shared_core.models.identity import User
from app.services import timetable_service

router = APIRouter(prefix="/timetables", tags=["timetables"])

@router.get("/me", response_model=List[CourseOfferingOut])
def get_my_timetable(
    current_user: User = Depends(require_role(["student"])),
    db: Session = Depends(get_db)
):
    return timetable_service.get_timetable_for_student(db, current_user.id)

@router.get("/lecturer/me", response_model=List[CourseOfferingOut])
def get_my_lecturer_timetable(
    current_user: User = Depends(require_role(["lecturer"])),
    db: Session = Depends(get_db)
):
    return timetable_service.get_timetable_for_lecturer(db, current_user.id)
