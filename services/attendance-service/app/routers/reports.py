from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from shared_core.db.session import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.models.identity import User
from shared_core.schemas.report import OfferingReport, TrendData, StudentSummary, WeeklyTrendItem

from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/offerings/{id}", response_model=OfferingReport)
def get_offering_report(
    id: UUID,
    current_user: User = Depends(require_role(["lecturer", "admin"])),
    db: Session = Depends(get_db)
):
    return report_service.get_offering_report(db, id)

@router.get("/offerings/{id}/trends", response_model=TrendData)
def get_offering_trends(
    id: UUID,
    current_user: User = Depends(require_role(["lecturer", "admin"])),
    db: Session = Depends(get_db)
):
    return report_service.get_offering_trends(db, id)

@router.get("/students/{id}/summary", response_model=StudentSummary)
def get_student_summary(
    id: UUID,
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    return report_service.get_student_summary(db, id)

@router.get("/trends/weekly", response_model=list[WeeklyTrendItem])
def get_weekly_trends(
    current_user: User = Depends(require_role(["admin", "lecturer"])),
    db: Session = Depends(get_db)
):
    return report_service.get_weekly_trends(db)

from fastapi.responses import Response
import csv
import io
from shared_core.models.attendance import AttendanceRecord, LectureSession

@router.get("/offerings/{id}/export")
def export_offering_report(id: UUID, current_user: User = Depends(require_role(["lecturer", "admin"])), db: Session = Depends(get_db)):
    if getattr(current_user.role, "value", current_user.role) == "lecturer":
        sessions = db.query(LectureSession).filter(LectureSession.course_offering_id == id).all()
        if sessions and any(s.course_offering.lecturer_id != current_user.id for s in sessions):
            raise HTTPException(status_code=403, detail="Forbidden")
    records = db.query(AttendanceRecord).join(LectureSession).filter(LectureSession.course_offering_id == id).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["record_id", "session_id", "student_id", "status", "first_check_in_at", "random_check_completed_at", "flag_reason"])
    for r in records:
        writer.writerow([r.id, r.lecture_session_id, r.student_id, r.status.value, r.first_check_in_at, r.random_check_completed_at, r.flag_reason or ""])
    return Response(content=buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=attendance-{id}.csv"})
