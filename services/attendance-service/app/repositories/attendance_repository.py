from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
import random
from sqlalchemy import cast, String, func
from sqlalchemy.orm import Session
from shared_core.models.attendance import LectureSession, VerificationWindow, AttendanceRecord, AttendanceVerificationAttempt
from shared_core.models.enums import SessionStatus, WindowType, AttendanceStatus, AttemptStatus


def create_session(db: Session, data: dict) -> LectureSession:
    if not data.get("session_number"):
        maximum = db.query(func.max(LectureSession.session_number)).filter(LectureSession.course_offering_id == data["course_offering_id"]).scalar()
        data["session_number"] = (maximum or 0) + 1
    obj = LectureSession(**data, status=SessionStatus.ongoing, held_at=datetime.now(timezone.utc))
    db.add(obj); db.commit(); db.refresh(obj); return obj


def get_session(db: Session, session_id: UUID):
    return db.query(LectureSession).filter(LectureSession.id == session_id).first()


def get_sessions(db: Session, offering_id=None, skip=0, limit=100, status=None):
    q = db.query(LectureSession).order_by(LectureSession.scheduled_at.desc())
    if offering_id: q = q.filter(LectureSession.course_offering_id == offering_id)
    if status:
        q = q.filter(cast(LectureSession.status, String) == status)
    return q.offset(skip).limit(min(limit, 200)).all()


def _window_type(value):
    return value.value if hasattr(value, "value") else str(value)


def schedule_check_in_window(db: Session, session: LectureSession, duration_mins: int = 15):
    now = datetime.now(timezone.utc)
    obj = VerificationWindow(
        lecture_session_id=session.id,
        window_type=WindowType.check_in,
        scheduled_open_at=now,
        scheduled_close_at=now + timedelta(minutes=duration_mins),
        actual_opened_at=now,
        is_active=True,
    )
    db.add(obj); db.commit(); db.refresh(obj); return obj


def schedule_random_window(db: Session, session: LectureSession, window_minutes: int):
    now = datetime.now(timezone.utc)
    obj = VerificationWindow(
        lecture_session_id=session.id,
        window_type=WindowType.random_check,
        scheduled_open_at=now,
        scheduled_close_at=now + timedelta(minutes=window_minutes),
        actual_opened_at=now,
        is_active=True,
    )
    db.add(obj); db.commit(); db.refresh(obj); return obj


def close_session(db: Session, session_id: UUID):
    session = get_session(db, session_id)
    if not session: return None
    now = datetime.now(timezone.utc)
    session.status = SessionStatus.completed
    for window in session.verification_windows:
        if window.is_active:
            window.is_active = False
            window.actual_closed_at = now
    enrolled = {e.student_id for e in session.course_offering.enrollments if e.is_active}
    existing = {r.student_id: r for r in session.attendance_records}
    for student_id in enrolled:
        record = existing.get(student_id)
        if record is None:
            db.add(AttendanceRecord(lecture_session_id=session.id, student_id=student_id, status=AttendanceStatus.absent))
        elif record.first_check_in_at and record.random_check_completed_at is None and not record.is_manually_overridden:
            record.status = AttendanceStatus.flagged_proxy
            record.flag_reason = record.flag_reason or "Random verification not completed"
    db.commit(); db.refresh(session); return session


def get_open_window(db: Session, lecture_session_id: UUID, window_type: str):
    now = datetime.now(timezone.utc)
    target = _window_type(window_type)
    q = db.query(VerificationWindow).filter(
        VerificationWindow.lecture_session_id == lecture_session_id,
        cast(VerificationWindow.window_type, String) == target,
        VerificationWindow.is_active.is_(True),
        VerificationWindow.scheduled_open_at <= now,
        VerificationWindow.scheduled_close_at > now,
    )
    return q.first()


def get_windows(db: Session, lecture_session_id: UUID):
    return db.query(VerificationWindow).filter(VerificationWindow.lecture_session_id == lecture_session_id).order_by(VerificationWindow.scheduled_open_at).all()


def get_attendance_record(db: Session, session_id: UUID, student_id: UUID):
    return db.query(AttendanceRecord).filter(AttendanceRecord.lecture_session_id == session_id, AttendanceRecord.student_id == student_id).first()


def create_or_get_record(db: Session, session_id: UUID, student_id: UUID):
    record = get_attendance_record(db, session_id, student_id)
    if not record:
        record = AttendanceRecord(lecture_session_id=session_id, student_id=student_id, status=AttendanceStatus.absent)
        db.add(record); db.flush()
    return record


def log_attempt(db: Session, data: dict):
    obj = AttendanceVerificationAttempt(**data)
    db.add(obj); db.commit(); db.refresh(obj); return obj


def find_attempt(db: Session, attempt_id: UUID):
    return db.query(AttendanceVerificationAttempt).filter(AttendanceVerificationAttempt.id == attempt_id).first()


def get_attendance_records(db: Session, session_id=None, student_id=None):
    q = db.query(AttendanceRecord).order_by(AttendanceRecord.created_at.desc())
    if session_id: q = q.filter(AttendanceRecord.lecture_session_id == session_id)
    if student_id: q = q.filter(AttendanceRecord.student_id == student_id)
    return q.all()


def get_attempts_for_record(db: Session, record_id: UUID):
    record = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
    if not record: return []
    windows = [x.id for x in record.lecture_session.verification_windows]
    if not windows: return []
    return db.query(AttendanceVerificationAttempt).filter(AttendanceVerificationAttempt.verification_window_id.in_(windows), AttendanceVerificationAttempt.student_id == record.student_id).order_by(AttendanceVerificationAttempt.attempted_at).all()


def get_recent_attempts(db: Session, offering_id=None, limit=50):
    q = db.query(AttendanceVerificationAttempt).join(VerificationWindow).join(LectureSession).order_by(AttendanceVerificationAttempt.attempted_at.desc())
    if offering_id: q = q.filter(LectureSession.course_offering_id == offering_id)
    return q.limit(min(limit, 200)).all()


def update_attendance_record(db: Session, record_id: UUID, data: dict):
    obj = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
    if not obj: return None
    for key, value in data.items():
        if hasattr(obj, key): setattr(obj, key, value)
    db.commit(); db.refresh(obj); return obj
