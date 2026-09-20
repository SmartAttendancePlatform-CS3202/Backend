from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo
from uuid import UUID, uuid4
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from shared_core.models.courses import CourseOffering
from shared_core.models.enums import AttemptStatus, AttendanceStatus, SessionStatus
from shared_core.schemas.events import FaceVerificationTask
from shared_core.models.identity import Student
from app.clients import scheduling_client
from app.repositories import attendance_repository
from app.utils.geofence import geofence_check
from app.rabbitmq.publisher import publish_verification_task
from shared_core.audit import audit


ATTENDANCE_EARLY_MINUTES = 15
DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _schedule_timezone():
    return ZoneInfo(os.environ.get("SCHEDULE_TIMEZONE", "Asia/Colombo"))


def _parse_clock(value: str | None) -> time | None:
    if not value:
        return None
    raw = value.strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    raise HTTPException(400, f"Invalid offering time format: {value}")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=_schedule_timezone()).astimezone(timezone.utc)
    return value.astimezone(timezone.utc)


def _occurrence_for_today(offering: CourseOffering, now_utc: datetime | None = None):
    now_utc = now_utc or datetime.now(timezone.utc)
    tz = _schedule_timezone()
    now_local = now_utc.astimezone(tz)
    if offering.day and offering.day.strip().lower() != DAY_NAMES[now_local.weekday()]:
        return None
    start_clock = _parse_clock(offering.start_time)
    end_clock = _parse_clock(offering.end_time)
    if not start_clock or not end_clock:
        raise HTTPException(400, "Offering start and end time must be configured before attendance can open")
    start_local = datetime.combine(now_local.date(), start_clock, tzinfo=tz)
    end_local = datetime.combine(now_local.date(), end_clock, tzinfo=tz)
    if end_local <= start_local:
        end_local += timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _session_status_for(now: datetime, start_at: datetime, end_at: datetime):
    if now < start_at:
        return SessionStatus.scheduled
    if now <= end_at:
        return SessionStatus.ongoing
    return SessionStatus.completed


def _sync_session_state(db: Session, session, now: datetime | None = None):
    now = now or datetime.now(timezone.utc)
    current = getattr(session.status, "value", session.status)
    if current in {"completed", "cancelled"}:
        for window in session.verification_windows:
            if window.is_active:
                window.is_active = False
                window.actual_closed_at = window.actual_closed_at or now
        db.commit()
        db.refresh(session)
        return session
    start_at = _as_utc(session.scheduled_at)
    end_at = start_at + timedelta(minutes=session.duration_mins)
    expected = _session_status_for(now, start_at, end_at)
    if session.status != expected:
        session.status = expected
        if expected == SessionStatus.ongoing and not session.held_at:
            session.held_at = now
        if expected == SessionStatus.completed:
            for window in session.verification_windows:
                if window.is_active:
                    window.is_active = False
                    window.actual_closed_at = window.actual_closed_at or now
        db.commit()
        db.refresh(session)
    return session


def _ensure_check_in_window(db: Session, session):
    open_at = _as_utc(session.scheduled_at) - timedelta(minutes=ATTENDANCE_EARLY_MINUTES)
    close_at = _as_utc(session.scheduled_at) + timedelta(minutes=session.duration_mins)
    window = attendance_repository.schedule_check_in_window(db, session, open_at=open_at, close_at=close_at)
    now = datetime.now(timezone.utc)
    should_be_active = open_at <= now < close_at and getattr(session.status, "value", session.status) != "completed"
    if window.is_active != should_be_active:
        window.is_active = should_be_active
        if not should_be_active and now >= close_at:
            window.actual_closed_at = window.actual_closed_at or close_at
        db.commit()
        db.refresh(window)
    return window


def _assert_session_access(session, current_user):
    role = str(getattr(current_user.role, "value", current_user.role))
    if role == "student":
        if not any(e.student_id == current_user.id and e.is_active for e in session.course_offering.enrollments):
            raise HTTPException(403, "Not enrolled in this session")
    elif role == "lecturer" and session.course_offering.lecturer_id != current_user.id:
        raise HTTPException(403, "Not assigned to this offering")


def _assert_student_enrolled(db: Session, student_id: UUID, session_id: UUID):
    session = attendance_repository.get_session(db, session_id)
    if not session: raise HTTPException(404, "Lecture session not found")
    active = [e for e in session.course_offering.enrollments if e.student_id == student_id and e.is_active]
    if not active: raise HTTPException(403, "Student is not enrolled in this offering")
    return session


def _venue_check(session, latitude, longitude):
    venue_id = session.venue_id or session.course_offering.venue_id
    if not venue_id: raise HTTPException(400, "Lecture venue is not configured")
    venue = scheduling_client.get_venue(venue_id)
    result = geofence_check(latitude, longitude, venue["shape_type"], venue["boundary_data"])
    return result, venue


def start_session(db: Session, data: dict, current_user):
    offering = scheduling_client.get_offering(data["course_offering_id"])
    if str(getattr(current_user.role, "value", current_user.role)) == "lecturer" and UUID(offering["lecturer_id"]) != current_user.id:
        raise HTTPException(403, "You are not assigned to this offering")
    session = attendance_repository.create_session(db, data)
    _ensure_check_in_window(db, session)
    return session


def get_or_create_scheduled_session(db: Session, offering_id: UUID, current_user, now: datetime | None = None):
    now = now or datetime.now(timezone.utc)
    offering = db.query(CourseOffering).filter(CourseOffering.id == offering_id).first()
    if not offering or not offering.is_active:
        raise HTTPException(404, "Offering not found")
    role = str(getattr(current_user.role, "value", current_user.role))
    if role == "lecturer" and offering.lecturer_id != current_user.id:
        raise HTTPException(403, "Forbidden")
    if role == "student" and not any(e.student_id == current_user.id and e.is_active for e in offering.enrollments):
        raise HTTPException(403, "Forbidden")

    occurrence = _occurrence_for_today(offering, now)
    if not occurrence:
        return None
    start_at, end_at = occurrence
    attendance_open_at = start_at - timedelta(minutes=ATTENDANCE_EARLY_MINUTES)
    if now < attendance_open_at or now > end_at:
        return None

    existing = attendance_repository.get_session_for_occurrence(db, offering.id, start_at)
    status = _session_status_for(now, start_at, end_at)
    if existing:
        session = _sync_session_state(db, existing, now)
    else:
        session = attendance_repository.create_scheduled_session(db, {
            "course_offering_id": offering.id,
            "venue_id": offering.venue_id,
            "verification_method_override": None,
            "scheduled_at": start_at,
            "duration_mins": int((end_at - start_at).total_seconds() // 60),
            "notes": "Auto-created from scheduled lecture offering",
        }, status)
    _ensure_check_in_window(db, session)
    attendance_repository.ensure_session_roster(db, session)
    return session


def get_active_scheduled_sessions(db: Session, current_user, offering_id: UUID | None = None):
    role = str(getattr(current_user.role, "value", current_user.role))
    q = db.query(CourseOffering).filter(CourseOffering.is_active.is_(True))
    if offering_id:
        q = q.filter(CourseOffering.id == offering_id)
    if role == "lecturer":
        q = q.filter(CourseOffering.lecturer_id == current_user.id)
    elif role == "student":
        q = q.filter(CourseOffering.enrollments.any(student_id=current_user.id, is_active=True))
    sessions = []
    for offering in q.all():
        session = get_or_create_scheduled_session(db, offering.id, current_user)
        if session:
            sessions.append(session)
    return sessions


def trigger_random_window(db: Session, session_id: UUID, current_user):
    session = attendance_repository.get_session(db, session_id)
    if not session: raise HTTPException(404, "Lecture session not found")
    _sync_session_state(db, session)
    if str(getattr(current_user.role, "value", current_user.role)) == "lecturer" and session.course_offering.lecturer_id != current_user.id:
        raise HTTPException(403, "You are not assigned to this offering")
    if getattr(session.status, "value", session.status) != "ongoing":
        raise HTTPException(400, "Session is not ongoing")
    
    # Check if a random window already exists for this session
    existing_window = next((w for w in session.verification_windows if getattr(w.window_type, "value", w.window_type) == "random_check"), None)
    if existing_window:
        raise HTTPException(400, "A random check-in window has already been triggered for this session")
        
    return attendance_repository.schedule_random_window(db, session, window_minutes=session.course_offering.random_check_window_minutes or 10)


def end_session(db: Session, session_id: UUID, current_user):
    session = attendance_repository.get_session(db, session_id)
    if not session: return None
    if str(getattr(current_user.role, "value", current_user.role)) == "lecturer" and session.course_offering.lecturer_id != current_user.id:
        raise HTTPException(403, "You are not assigned to this offering")
    return attendance_repository.close_session(db, session_id)


def _window_payload(window, include_identity: bool = True):
    if not window: return None
    payload={
        "id": window.id,
        "lecture_session_id": window.lecture_session_id,
        "window_type": getattr(window.window_type,"value",window.window_type),
        "scheduled_open_at": window.scheduled_open_at,
        "scheduled_close_at": window.scheduled_close_at,
        "actual_opened_at": window.actual_opened_at,
        "actual_closed_at": window.actual_closed_at,
        "is_active": window.is_active,
        "opened_at": window.actual_opened_at,
        "closed_at": window.actual_closed_at,
    }
    if not include_identity:
        payload.pop("id",None)
    return payload

def get_active_windows(db: Session, lecture_session_id: UUID, student_id: UUID | None = None):
    session = attendance_repository.get_session(db, lecture_session_id)
    if session:
        _sync_session_state(db, session)
        _ensure_check_in_window(db, session)
    check = attendance_repository.get_open_window(db, lecture_session_id, "check_in")
    random_window = attendance_repository.get_open_window(db, lecture_session_id, "random_check")
    return {
        "check_in_window": _window_payload(check),
        "random_check_active": bool(random_window),
        # The exact random window identifier is only exposed while the window is open.
        "random_check_window": _window_payload(random_window) if random_window and student_id else None,
    }


def get_session_windows(db: Session, lecture_session_id: UUID):
    session = attendance_repository.get_session(db, lecture_session_id)
    if session:
        _sync_session_state(db, session)
        _ensure_check_in_window(db, session)
    return [_window_payload(window) for window in attendance_repository.get_windows(db, lecture_session_id)]


async def record_check_in(db: Session, student_id: UUID, payload):
    session = _assert_student_enrolled(db, student_id, payload.lecture_session_id)
    _sync_session_state(db, session)
    _ensure_check_in_window(db, session)
    window = attendance_repository.get_open_window(db, session.id, "check_in")
    if not window: raise HTTPException(400, "No active check-in window")
    record = attendance_repository.get_attendance_record(db, session.id, student_id)
    if record and record.first_check_in_at:
        raise HTTPException(409, "Attendance check-in already recorded")
    geo, _ = _venue_check(session, payload.latitude, payload.longitude)
    now = datetime.now(timezone.utc)
    attempt_id = uuid4()
    if not geo["inside"]:
        attendance_repository.log_attempt(db, {
            "id": attempt_id, "verification_window_id": window.id, "student_id": student_id, "used_location_check": True,
            "location_method": "gps_geofence", "latitude": payload.latitude, "longitude": payload.longitude,
            "distance_from_venue_meters": geo.get("distance_meters"), "status": AttemptStatus.failed,
            "failure_reason": "Outside geofence", "attempted_at": now,
        })
        raise HTTPException(400, "Location check failed: outside geofence")
        
    task = FaceVerificationTask(
        event_id=uuid4(), attempt_id=attempt_id, student_id=student_id, verification_window_id=window.id,
        face_image_base64=payload.face_image_base64, latitude=payload.latitude, longitude=payload.longitude,
    )
    try:
        await publish_verification_task(task)
    except Exception as exc:
        attendance_repository.log_attempt(db, {
            "id": attempt_id, "verification_window_id": window.id, "student_id": student_id,
            "used_face_verification": True, "used_location_check": True, "location_method": "gps_geofence",
            "latitude": payload.latitude, "longitude": payload.longitude,
            "distance_from_venue_meters": geo.get("distance_meters"), "status": AttemptStatus.failed,
            "failure_reason": f"Queue unavailable: {exc}", "attempted_at": now,
        })
        raise HTTPException(503, "Face verification queue unavailable") from exc
    return {"status": "processing", "attempt_id": attempt_id}



def record_random_check(db: Session, student_id: UUID, payload):
    session = _assert_student_enrolled(db, student_id, payload.lecture_session_id)
    _sync_session_state(db, session)
    active = attendance_repository.get_open_window(db, session.id, "random_check")
    if not active or active.id != payload.verification_window_id:
        raise HTTPException(400, "No active random verification window")
    geo, _ = _venue_check(session, payload.latitude, payload.longitude)
    attempt_id = uuid4()
    if not geo["inside"]:
        attempt = attendance_repository.log_attempt(db, {
            "id": attempt_id, "verification_window_id": active.id, "student_id": student_id,
            "used_face_verification": False, "used_location_check": True, "location_method": "gps_geofence",
            "latitude": payload.latitude, "longitude": payload.longitude,
            "distance_from_venue_meters": geo.get("distance_meters"), "status": AttemptStatus.failed,
            "failure_reason": "Outside geofence",
        })
        return {"status": "rejected", "attempt_id": attempt_id, "reason": "outside_geofence"}

    attempt = attendance_repository.log_attempt(db, {
        "id": attempt_id, "verification_window_id": active.id, "student_id": student_id,
        "used_face_verification": False, "used_location_check": True, "location_method": "gps_geofence",
        "latitude": payload.latitude, "longitude": payload.longitude,
        "distance_from_venue_meters": geo.get("distance_meters"), "status": AttemptStatus.success,
        "attempted_at": datetime.now(timezone.utc),
    })
    
    # Update random check completed at
    record = attendance_repository.get_attendance_record(db, session.id, student_id)
    if record:
        record.random_check_completed_at = datetime.now(timezone.utc)
        db.commit()
        
    return {"status": "success", "attempt_id": attempt_id}


def get_student_attendance(db, student_id): return attendance_repository.get_attendance_records(db, student_id=student_id)

def get_records(db, session_id=None, student_id=None): return attendance_repository.get_attendance_records(db, session_id=session_id, student_id=student_id)
def get_attendance_attempts(db, record_id): return attendance_repository.get_attempts_for_record(db, record_id)
def get_recent_attempts(db, offering_id=None): return attendance_repository.get_recent_attempts(db, offering_id)

def get_sessions(db, offering_id=None, skip=0, limit=100, status=None): return attendance_repository.get_sessions(db, offering_id, skip, limit, status)

def get_session(db, session_id):
    session = attendance_repository.get_session(db, session_id)
    if session:
        _sync_session_state(db, session)
        _ensure_check_in_window(db, session)
        attendance_repository.ensure_session_roster(db, session)
    return session


def override_record(db: Session, record_id: UUID, user_id: UUID, override_data: dict):
    allowed = {"present", "late", "absent", "flagged_proxy"}
    if override_data.get("status") not in allowed: raise HTTPException(400, "Invalid attendance status")
    record = attendance_repository.update_attendance_record(db, record_id, {
        **override_data, "is_manually_overridden": True, "override_by": user_id,
        "overridden_at": datetime.now(timezone.utc),
    })
    if record:
        audit(db, user_id, "attendance.override", "attendance_record", record.id, new_data={"status": record.status.value, "reason": record.override_reason})
        db.commit()
    return record
