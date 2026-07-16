from uuid import UUID

from fastapi import APIRouter, Depends

from shared_core.auth.rbac import require_role

from app.services import attendance_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/offerings/{course_offering_id}", dependencies=[Depends(require_role("lecturer", "admin"))])
def offering_report(course_offering_id: UUID):
    """Attendance percentage, absentees, and late arrivals for one offering —
    backs the web dashboard's analytics view."""
    return attendance_service.get_offering_report(course_offering_id)
