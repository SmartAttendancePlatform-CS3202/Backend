from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, String
from datetime import datetime, timedelta, timezone
import random

from shared_core.models.attendance import LectureSession, VerificationWindow, AttendanceRecord, AttendanceVerificationAttempt, Venue
from shared_core.models.enums import SessionStatus, WindowType, AttendanceStatus

def create_session(db: Session, data: dict) -> LectureSession:
    # Auto-increment session number for this offering if not explicitly provided
    if not data.get('session_number'):
        max_session = db.query(func.max(LectureSession.session_number)).filter(LectureSession.course_offering_id == data['course_offering_id']).scalar()
        data['session_number'] = (max_session or 0) + 1
    
    db_obj = LectureSession(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_session(db: Session, session_id: UUID) -> Optional[LectureSession]:
    return db.query(LectureSession).filter(LectureSession.id == session_id).first()

def get_sessions(db: Session, offering_id: Optional[UUID] = None, skip: int = 0, limit: int = 100) -> List[LectureSession]:
    query = db.query(LectureSession)
    if offering_id:
        query = query.filter(LectureSession.course_offering_id == offering_id)
    return query.offset(skip).limit(limit).all()

def schedule_check_in_window(db: Session, session: LectureSession, duration_mins: int = 15) -> VerificationWindow:
    now = datetime.now(timezone.utc)
    window = VerificationWindow(
        lecture_session_id=session.id,
        window_type=WindowType.first_check_in,
        scheduled_open_at=now,
        scheduled_close_at=now + timedelta(minutes=duration_mins),
        actual_opened_at=now,
        is_active=True
    )
    db.add(window)
    db.commit()
    db.refresh(window)
    return window

def schedule_random_window(db: Session, session: LectureSession, window_minutes: int) -> VerificationWindow:
    now = datetime.now(timezone.utc)
    # Schedule sometime between now + 15 mins and session end - window_minutes
    start_offset = 15
    end_offset = max(15, session.duration_mins - window_minutes)
    
    if start_offset < end_offset:
        random_start_offset = random.randint(start_offset, end_offset)
    else:
        random_start_offset = start_offset
        
    scheduled_start = now + timedelta(minutes=random_start_offset)
    window = VerificationWindow(
        lecture_session_id=session.id,
        window_type=WindowType.random_check,
        scheduled_open_at=scheduled_start,
        scheduled_close_at=scheduled_start + timedelta(minutes=window_minutes),
        actual_opened_at=scheduled_start,
        is_active=True
    )
    db.add(window)
    db.commit()
    db.refresh(window)
    return window

def close_session(db: Session, session_id: UUID) -> Optional[LectureSession]:
    session = get_session(db, session_id)
    if session:
        session.status = SessionStatus.completed
        session.held_at = session.scheduled_at
        db.commit()
        db.refresh(session)
    return session

def get_open_window(db: Session, lecture_session_id: UUID, window_type: str) -> Optional[VerificationWindow]:
    now = datetime.now(timezone.utc)
    target_type = window_type.value if hasattr(window_type, 'value') else str(window_type)
    return db.query(VerificationWindow).filter(
        VerificationWindow.lecture_session_id == lecture_session_id,
        cast(VerificationWindow.window_type, String) == target_type,
        VerificationWindow.is_active.is_(True),
        (
            (VerificationWindow.actual_opened_at <= now) |
            (VerificationWindow.scheduled_open_at <= now)
        ),
        (VerificationWindow.actual_closed_at.is_(None) | (VerificationWindow.actual_closed_at > now)) &
        (VerificationWindow.scheduled_close_at > now)
    ).first()

def log_attempt(db: Session, data: dict) -> AttendanceVerificationAttempt:
    attempt = AttendanceVerificationAttempt(**data)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt

def upsert_first_check_in(db: Session, lecture_session_id: UUID, student_id: UUID, attempt_data: dict) -> AttendanceRecord:
    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.lecture_session_id == lecture_session_id,
        AttendanceRecord.student_id == student_id
    ).first()
    
    now = datetime.now(timezone.utc)
    if not record:
        record = AttendanceRecord(
            lecture_session_id=lecture_session_id,
            student_id=student_id,
            status=AttendanceStatus.present,
            first_check_in_at=now
        )
        db.add(record)
    else:
        record.first_check_in_at = now
        record.status = AttendanceStatus.present
        
    db.commit()
    db.refresh(record)
    return record

def update_random_check_status(db: Session, verification_window_id: UUID, student_id: UUID, attempt_data: dict) -> Optional[AttendanceRecord]:
    window = db.query(VerificationWindow).filter(VerificationWindow.id == verification_window_id).first()
    if not window:
        return None
        
    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.lecture_session_id == window.lecture_session_id,
        AttendanceRecord.student_id == student_id
    ).first()
    
    if record:
        record.random_check_completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(record)
    return record

def get_attendance_records(db: Session, session_id: Optional[UUID] = None, student_id: Optional[UUID] = None) -> List[AttendanceRecord]:
    query = db.query(AttendanceRecord)
    if session_id:
        query = query.filter(AttendanceRecord.lecture_session_id == session_id)
    if student_id:
        query = query.filter(AttendanceRecord.student_id == student_id)
    return query.all()

def update_attendance_record(db: Session, record_id: UUID, update_data: dict) -> Optional[AttendanceRecord]:
    record = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
    if not record:
        return None
    for key, val in update_data.items():
        if hasattr(record, key):
            setattr(record, key, val)
    db.commit()
    db.refresh(record)
    return record
    
def get_attempts(db: Session, record_id: UUID) -> List[AttendanceVerificationAttempt]:
    record = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
    if not record:
        return []
    
    windows = db.query(VerificationWindow).filter(VerificationWindow.lecture_session_id == record.lecture_session_id).all()
    window_ids = [w.id for w in windows]
    if not window_ids:
        return []
    
    return db.query(AttendanceVerificationAttempt).filter(
        AttendanceVerificationAttempt.verification_window_id.in_(window_ids),
        AttendanceVerificationAttempt.student_id == record.student_id
    ).all()

def get_recent_attempts(db: Session, offering_id: Optional[UUID] = None, limit: int = 50) -> List[AttendanceVerificationAttempt]:
    query = db.query(AttendanceVerificationAttempt).order_by(AttendanceVerificationAttempt.attempted_at.desc())
    if offering_id:
        query = (
            query.join(VerificationWindow, AttendanceVerificationAttempt.verification_window_id == VerificationWindow.id)
                 .join(LectureSession, VerificationWindow.lecture_session_id == LectureSession.id)
                 .filter(LectureSession.course_offering_id == offering_id)
        )
    return query.limit(limit).all()
