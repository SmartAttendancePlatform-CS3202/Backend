from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from shared_core.db.session import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.models.identity import User
from shared_core.schemas.report import OfferingReport, TrendData, StudentSummary

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
