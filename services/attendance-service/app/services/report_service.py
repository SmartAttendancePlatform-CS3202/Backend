from __future__ import annotations
from collections import defaultdict
from uuid import UUID
from sqlalchemy.orm import Session
from shared_core.models.attendance import AttendanceRecord, LectureSession
from shared_core.models.courses import CourseOffering, Enrollment
from shared_core.models.identity import Student
from shared_core.schemas.report import OfferingReport, TrendData, TrendDataPoint, StudentSummary, WeeklyTrendItem, StudentAttendanceDetail

def _percent(present: int, total: int) -> float:
    return round((present / total) * 100, 2) if total else 0.0

def _student_detail(r: AttendanceRecord) -> StudentAttendanceDetail:
    return StudentAttendanceDetail(student_id=r.student_id, status=r.status.value, first_check_in_at=r.first_check_in_at.isoformat() if r.first_check_in_at else None, random_check_completed_at=r.random_check_completed_at.isoformat() if r.random_check_completed_at else None, flag_reason=r.flag_reason)

def get_offering_report(db: Session, course_offering_id: UUID) -> OfferingReport:
    sessions = db.query(LectureSession).filter(LectureSession.course_offering_id == course_offering_id).order_by(LectureSession.scheduled_at).all()
    enrollments = db.query(Enrollment).filter(Enrollment.course_offering_id == course_offering_id, Enrollment.is_active.is_(True)).all()
    enrolled_ids = {e.student_id for e in enrollments}
    if not sessions or not enrolled_ids:
        return OfferingReport(course_offering_id=course_offering_id, attendance_percentage=0.0, absentee_list=[], late_arrival_list=[])
    records = [r for s in sessions for r in s.attendance_records]
    latest_by_student = {}
    for r in records:
        latest_by_student[r.student_id] = r
    present = sum(r.status.value in {"present", "late"} for r in records)
    total = len(sessions) * len(enrolled_ids)
    absent = []
    late = []
    for sid in enrolled_ids:
        r = latest_by_student.get(sid)
        if r and r.status.value == "late": late.append(_student_detail(r))
        if not r or r.status.value == "absent":
            if r: absent.append(_student_detail(r))
            else: absent.append(StudentAttendanceDetail(student_id=sid, status="absent"))
    return OfferingReport(course_offering_id=course_offering_id, attendance_percentage=_percent(present, total), absentee_list=absent, late_arrival_list=late)

def get_offering_trends(db: Session, course_offering_id: UUID) -> TrendData:
    sessions = db.query(LectureSession).filter(LectureSession.course_offering_id == course_offering_id).order_by(LectureSession.scheduled_at).all()
    enrollment_total = db.query(Enrollment).filter(Enrollment.course_offering_id == course_offering_id, Enrollment.is_active.is_(True)).count()
    points = []
    for s in sessions:
        ok = sum(r.status.value in {"present", "late"} for r in s.attendance_records)
        points.append(TrendDataPoint(date=s.scheduled_at.date().isoformat(), attendance_percentage=_percent(ok, enrollment_total or len(s.attendance_records))))
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
    return [WeeklyTrendItem(week=f"{year}-W{week:02d}", attendance_rate=_percent(sum(r.status.value in {"present", "late"} for r in records), len(records)), total_students=len(records)) for (year, week), records in sorted(buckets.items())]
