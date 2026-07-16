from uuid import UUID

from fastapi import APIRouter, Depends

from shared_core.auth.rbac import require_role
from shared_core.schemas.session import LectureSessionOut

from app.services import attendance_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=LectureSessionOut, dependencies=[Depends(require_role("lecturer", "admin"))])
def start_session(course_offering_id: UUID):
    """Creates a lecture_sessions row and schedules the random verification
    window server-side (opens at an unpredictable point during the lecture —
    never exposed to the student's app before it opens)."""
    return attendance_service.start_session(course_offering_id)


@router.post("/{session_id}/end", dependencies=[Depends(require_role("lecturer", "admin"))])
def end_session(session_id: UUID):
    return attendance_service.end_session(session_id)
