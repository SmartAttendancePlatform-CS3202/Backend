from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories import attendance_repository
from shared_core.schemas.report import OfferingReport, TrendData, StudentSummary
import random

def get_offering_report(db: Session, course_offering_id: UUID) -> OfferingReport:
    # Stub: Returns empty lists since we need a complex query for actual report
    # Typically this would aggregate all sessions and records
    return OfferingReport(
        course_offering_id=course_offering_id,
        attendance_percentage=random.uniform(70.0, 99.9),
        absentee_list=[],
        late_arrival_list=[]
    )

def get_offering_trends(db: Session, course_offering_id: UUID) -> TrendData:
    # Stub
    return TrendData(
        course_offering_id=course_offering_id,
        trends=[]
    )

def get_student_summary(db: Session, student_id: UUID) -> StudentSummary:
    # Stub
    return StudentSummary(
        student_id=student_id,
        overall_attendance_percentage=random.uniform(50.0, 100.0),
        course_breakdown={}
    )
