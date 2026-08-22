from __future__ import annotations
from collections import defaultdict
from datetime import date
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func
from shared_core.models.attendance import AttendanceRecord, LectureSession
from shared_core.models.courses import CourseOffering, Enrollment
from shared_core.schemas.report import OfferingReport, TrendData, TrendDataPoint, StudentSummary, WeeklyTrendItem, StudentAttendanceDetail


def _percent(present: int, total: int) -> float:
    return round((present / total) * 100, 2) if total else 0.0


def get_offering_report(db: Session, course_offering_id: UUID) -> OfferingReport:
    session_ids = [s.id for s in db.query(LectureSession.id).filter(LectureSession.course_offering_id == course_offering_id).all()]
    records = db.query(AttendanceRecord).filter(AttendanceRecord.lecture_session_id.in_(session_ids)).all() if session_ids else []
    latest_by_student = {}
    for r in records: latest_by_student[r.student_id] = r
    vals = list(latest_by_student.values())
    present = sum(r.status.value in {"present", "late"} for r in vals)
    absentees = [StudentAttendanceDetail(student_id=r.student_id, status=r.status.value, first_check_in_at=r.first_check_in_at.isoformat() if r.first_check_in_at else None, random_check_completed_at=r.random_check_completed_at.isoformat() if r.random_check_completed_at else None, flag_reason=r.flag_reason) for r in vals if r.status.value == "absent"]
    late = [StudentAttendanceDetail(student_id=r.student_id, status=r.status.value, first_check_in_at=r.first_check_in_at.isoformat() if r.first_check_in_at else None, random_check_completed_at=r.random_check_completed_at.isoformat() if r.random_check_completed_at else None, flag_reason=r.flag_reason) for r in vals if r.status.value == "late"]
    return OfferingReport(course_offering_id=course_offering_id, attendance_percentage=_percent(present, len(vals)), absentee_list=absentees, late_arrival_list=late)


def get_offering_trends(db: Session, course_offering_id: UUID) -> TrendData:
    sessions = db.query(LectureSession).filter(LectureSession.course_offering_id == course_offering_id).order_by(LectureSession.scheduled_at).all()
    points = []
    for s in sessions:
        records = s.attendance_records
        ok = sum(r.status.value in {"present", "late"} for r in records)
        points.append(TrendDataPoint(date=s.scheduled_at.date().isoformat(), attendance_percentage=_percent(ok, len(records))))
    return TrendData(course_offering_id=course_offering_id, trends=points)


def get_student_summary(db: Session, student_id: UUID) -> StudentSummary:
    records = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student_id).all()
    by_offering = defaultdict(list)
    for r in records: by_offering[r.lecture_session.course_offering_id].append(r)
    breakdown = {str(k): _percent(sum(x.status.value in {"present", "late"} for x in v), len(v)) for k,v in by_offering.items()}
    return StudentSummary(student_id=student_id, overall_attendance_percentage=_percent(sum(r.status.value in {"present", "late"} for r in records), len(records)), course_breakdown=breakdown)


def get_weekly_trends(db: Session):
    rows = db.query(LectureSession).order_by(LectureSession.scheduled_at).all()
    buckets = defaultdict(list)
    for s in rows:
        week = s.scheduled_at.date().isocalendar()[:2]
        buckets[week].extend(s.attendance_records)
    out = []
    for (year, week), records in sorted(buckets.items()):
        out.append(WeeklyTrendItem(week=f"{year}-W{week:02d}", attendance_rate=_percent(sum(r.status.value in {"present", "late"} for r in records), len(records)), total_students=len(records)))
    return out
