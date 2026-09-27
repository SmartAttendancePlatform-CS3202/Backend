from __future__ import annotations

import os
import math
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo
from uuid import UUID, uuid4
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from shared_core.models.courses import CourseOffering, Enrollment
from shared_core.models.enums import AttemptStatus, AttendanceStatus, SessionStatus
from shared_core.schemas.events import FaceVerificationTask
from shared_core.models.identity import Student, User
from shared_core.models.vision import FaceProfile
from shared_core.models.attendance import AttendanceRecord, LectureSession, Venue
from app.clients import scheduling_client, ai_vision_client
from app.repositories import attendance_repository
from app.utils.geofence import geofence_check, calculate_distance
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
    session = resolve_session(db, session_id, student_id=student_id)
    if not session: raise HTTPException(404, "Lecture session not found")
    active = [e for e in session.course_offering.enrollments if e.student_id == student_id and e.is_active]
    if not active: raise HTTPException(403, "Student is not enrolled in this offering")
    return session


def _venue_check(session, latitude, longitude):
    venue_id = session.venue_id or (session.course_offering.venue_id if session.course_offering else None)
    if not venue_id: raise HTTPException(400, "Lecture venue is not configured")
    try:
        venue = scheduling_client.get_venue(venue_id)
    except Exception:
        db_venue = session.venue or (session.course_offering.venue if session.course_offering else None)
        if db_venue and isinstance(db_venue.boundary_data, dict):
            venue = {
                "id": str(db_venue.id),
                "name": db_venue.name,
                "building": db_venue.building,
                "shape_type": getattr(db_venue, "shape_type", "circle") or "circle",
                "boundary_data": db_venue.boundary_data,
            }
        else:
            venue = {
                "id": str(venue_id),
                "name": "Lecture Hall",
                "building": "Campus",
                "shape_type": "circle",
                "boundary_data": {"latitude": 6.7951, "longitude": 79.9009, "radius_meters": 30.0},
            }
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


def resolve_session(db: Session, session_id: UUID, student_id: UUID | None = None, now: datetime | None = None) -> LectureSession | None:
    now = now or datetime.now(timezone.utc)

    # 1. Direct match by session id in lecture_sessions table
    session = attendance_repository.get_session(db, session_id)
    if session:
        _sync_session_state(db, session, now)
        _ensure_check_in_window(db, session)
        return session

    # 2. Check if session_id is a course_offering_id
    offering = db.query(CourseOffering).filter(CourseOffering.id == session_id).first()
    if offering:
        today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
        today_end = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)

        # 2a. Look for an existing ongoing lecture session for this course offering
        session = (
            db.query(LectureSession)
            .filter(
                LectureSession.course_offering_id == offering.id,
                LectureSession.status == SessionStatus.ongoing,
            )
            .order_by(LectureSession.scheduled_at.desc())
            .first()
        )
        if not session:
            # 2b. Look for a session scheduled for today
            session = (
                db.query(LectureSession)
                .filter(
                    LectureSession.course_offering_id == offering.id,
                    LectureSession.scheduled_at >= today_start,
                    LectureSession.scheduled_at <= today_end,
                )
                .order_by(LectureSession.scheduled_at.desc())
                .first()
            )
        if not session and student_id:
            student_user = db.query(User).filter(User.id == student_id).first()
            if student_user:
                try:
                    session = get_or_create_scheduled_session(db, offering.id, student_user, now=now)
                except Exception:
                    session = None

        if not session:
            # 2c. Auto-create ongoing session for this offering so student check-in proceeds
            session = attendance_repository.create_scheduled_session(db, {
                "course_offering_id": offering.id,
                "venue_id": offering.venue_id,
                "verification_method_override": None,
                "scheduled_at": now,
                "duration_mins": 120,
                "notes": "Auto-created from student check-in request",
            }, SessionStatus.ongoing)

        if session:
            _sync_session_state(db, session, now)
            _ensure_check_in_window(db, session)
            attendance_repository.ensure_session_roster(db, session)
            return session

    # 3. If student is specified, check if student has any active session currently ongoing
    if student_id:
        active_session = (
            db.query(LectureSession)
            .join(CourseOffering, LectureSession.course_offering_id == CourseOffering.id)
            .join(Enrollment, CourseOffering.id == Enrollment.course_offering_id)
            .filter(
                Enrollment.student_id == student_id,
                Enrollment.is_active.is_(True),
                LectureSession.status == SessionStatus.ongoing,
            )
            .order_by(LectureSession.scheduled_at.desc())
            .first()
        )
        if active_session:
            _sync_session_state(db, active_session, now)
            _ensure_check_in_window(db, active_session)
            return active_session

    return None


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
    session = resolve_session(db, lecture_session_id, student_id=student_id)
    if session:
        _sync_session_state(db, session)
        _ensure_check_in_window(db, session)
        actual_session_id = session.id
    else:
        actual_session_id = lecture_session_id

    check = attendance_repository.get_open_window(db, actual_session_id, "check_in")
    random_window = attendance_repository.get_open_window(db, actual_session_id, "random_check")
    venue_geofence = None
    if session:
        venue_id = session.venue_id or (session.course_offering.venue_id if session.course_offering else None)
        if venue_id:
            try:
                venue = scheduling_client.get_venue(venue_id)
                boundary = venue.get("boundary_data", {})
                lat = boundary.get("latitude") or (boundary.get("center", {}).get("lat") if isinstance(boundary.get("center"), dict) else None)
                lng = boundary.get("longitude") or (boundary.get("center", {}).get("lng") if isinstance(boundary.get("center"), dict) else None)
                rad = boundary.get("radius_meters") or boundary.get("radius_m") or 30
                venue_geofence = {
                    "venue_name": venue.get("name", "Lecture Hall"),
                    "building": venue.get("building"),
                    "latitude": float(lat) if lat is not None else 6.7951,
                    "longitude": float(lng) if lng is not None else 79.9009,
                    "radius_meters": int(rad),
                }
            except Exception:
                db_venue = session.venue or (session.course_offering.venue if session.course_offering else None)
                if db_venue and isinstance(db_venue.boundary_data, dict):
                    lat = db_venue.boundary_data.get("latitude", 6.7951)
                    lng = db_venue.boundary_data.get("longitude", 79.9009)
                    rad = db_venue.boundary_data.get("radius_meters", 30)
                    venue_geofence = {
                        "venue_name": db_venue.name,
                        "building": db_venue.building,
                        "latitude": float(lat),
                        "longitude": float(lng),
                        "radius_meters": int(rad),
                    }

    return {
        "check_in_window": _window_payload(check),
        "random_check_active": bool(random_window),
        "random_check_window": _window_payload(random_window) if random_window and student_id else None,
        "venue_geofence": venue_geofence,
        "lecture_session_id": str(actual_session_id),
    }


def get_session_windows(db: Session, lecture_session_id: UUID):
    session = attendance_repository.get_session(db, lecture_session_id)
    if session:
        _sync_session_state(db, session)
        _ensure_check_in_window(db, session)
    return [_window_payload(window) for window in attendance_repository.get_windows(db, lecture_session_id)]


def verify_location_precheck(db: Session, student_id: UUID, payload):
    now = datetime.now(timezone.utc)
    session_id_str = str(payload.lecture_session_id)
    is_test_class = (session_id_str == "TEST_MOCK_CLASS")

    if is_test_class:
        if payload.latitude is None or payload.longitude is None:
            return {
                "success": False,
                "inside": False,
                "distance_meters": None,
                "radius_meters": 30.0,
                "venue_name": "CSE Seminar Room",
                "message": "Missing GPS coordinates",
            }
        dist = calculate_distance(payload.latitude, payload.longitude, 6.7951, 79.9009)
        radius = 30.0
        inside = dist <= radius
        return {
            "success": True,
            "inside": inside,
            "distance_meters": round(dist, 2),
            "radius_meters": radius,
            "venue_name": "CSE Seminar Room",
            "lecture_session_id": "TEST_MOCK_CLASS",
            "message": "Within geofence" if inside else f"Outside geofence ({round(dist)}m away, must be <= {round(radius)}m)",
        }

    try:
        session_uuid = UUID(session_id_str)
    except ValueError:
        raise HTTPException(400, "Invalid lecture session ID format")

    session = resolve_session(db, session_uuid, student_id=student_id, now=now)
    if not session:
        raise HTTPException(404, "Lecture session not found")

    geo, venue = _venue_check(session, payload.latitude, payload.longitude)
    inside = bool(geo.get("inside"))
    dist = geo.get("distance_meters")
    radius = 30.0
    if venue and isinstance(venue.get("boundary_data"), dict):
        radius = float(venue["boundary_data"].get("radius_meters", venue["boundary_data"].get("radius_m", 30.0)))

    if not inside:
        window = attendance_repository.get_open_window(db, session.id, "check_in")
        if window:
            attendance_repository.log_attempt(db, {
                "id": uuid4(),
                "verification_window_id": window.id,
                "student_id": student_id,
                "attempt_number": 1,
                "used_face_verification": False,
                "used_location_check": True,
                "location_method": "gps_geofence",
                "latitude": payload.latitude,
                "longitude": payload.longitude,
                "distance_from_venue_meters": dist,
                "status": AttemptStatus.failed,
                "failure_reason": "Outside geofence",
                "attempted_at": now,
            })

    return {
        "success": True,
        "inside": inside,
        "distance_meters": round(dist, 2) if dist is not None else None,
        "radius_meters": radius,
        "venue_name": venue.get("name", "Lecture Hall"),
        "lecture_session_id": str(session.id),
        "message": "Within geofence" if inside else f"Outside geofence ({round(dist or 0)}m away, must be <= {round(radius)}m)",
    }


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
        face_embedding=payload.face_embedding, latitude=payload.latitude, longitude=payload.longitude,
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


async def record_random_check(db: Session, student_id: UUID, payload):
    session = _assert_student_enrolled(db, student_id, payload.lecture_session_id)
    _sync_session_state(db, session)
    active = attendance_repository.get_open_window(db, session.id, "random_check")
    if not active or active.id != payload.verification_window_id:
        raise HTTPException(400, "No active random verification window")
    geo, _ = _venue_check(session, payload.latitude, payload.longitude)
    attempt_id = uuid4()
    if not geo["inside"]:
        attendance_repository.log_attempt(db, {
            "id": attempt_id, "verification_window_id": active.id, "student_id": student_id,
            "used_face_verification": False, "used_location_check": True, "location_method": "gps_geofence",
            "latitude": payload.latitude, "longitude": payload.longitude,
            "distance_from_venue_meters": geo.get("distance_meters"), "status": AttemptStatus.failed,
            "failure_reason": "Outside geofence",
        })
        return {"status": "rejected", "attempt_id": attempt_id, "reason": "outside_geofence"}

    attendance_repository.log_attempt(db, {
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

def get_records(db, session_id=None, student_id=None):
    if session_id:
        session = attendance_repository.get_session(db, session_id)
        if session:
            attendance_repository.ensure_session_roster(db, session)
    return attendance_repository.get_attendance_records(db, session_id=session_id, student_id=student_id)

def get_attendance_attempts(db, record_id): return attendance_repository.get_attempts_for_record(db, record_id)

def get_recent_attempts(db, offering_id=None): return attendance_repository.get_recent_attempts(db, offering_id)

def get_sessions(db, offering_id=None, skip=0, limit=100, status=None): return attendance_repository.get_sessions(db, offering_id, skip, limit, status)

def get_session(db, session_id):
    session = attendance_repository.get_session(db, session_id)
    if session:
        _sync_session_state(db, session)
        _ensure_check_in_window(db, session)
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


def verify_face_and_record_attendance(db: Session, student_id: UUID, payload):
    now = datetime.now(timezone.utc)
    attempt_id = uuid4()

    # 1. Fetch active face profile from database
    profile = db.query(FaceProfile).filter(
        FaceProfile.student_id == student_id,
        FaceProfile.is_active.is_(True)
    ).first()

    if not profile:
        return {
            "success": False,
            "is_match": False,
            "confidence": 0.0,
            "threshold": 0.70,
            "message": "No active face biometric profile registered for student. Please complete face registration first.",
        }

    # 2. Perform biometric matching (via AI Vision microservice or direct vector similarity)
    threshold = float(os.environ.get("FACE_SIMILARITY_THRESHOLD", "0.70"))
    match_result = None
    live_depth = getattr(payload, "depth_features", None)
    try:
        match_result = ai_vision_client.verify_face(
            str(student_id),
            payload.face_embedding,
            depth_features=live_depth,
        )
    except Exception:
        # Fallback to direct in-memory cosine similarity against stored DB profile
        pass

    if match_result and ("is_match" in match_result or "requires_re_registration" in match_result):
        if match_result.get("requires_re_registration"):
            return {
                "success": False,
                "is_match": False,
                "confidence": 0.0,
                "threshold": threshold,
                "requires_re_registration": True,
                "message": match_result.get(
                    "message",
                    "Face profile was enrolled with an outdated model version. Please re-register your face profile.",
                ),
            }
        is_match = bool(match_result.get("is_match"))
        confidence = float(match_result.get("confidence", 0.0))
    else:
        # Check enrollment version on fallback
        enrollment_version_raw = getattr(profile, "enrollment_version", 4)
        try:
            if isinstance(enrollment_version_raw, (int, float, str)):
                enrollment_version = int(enrollment_version_raw)
            else:
                enrollment_version = 4
        except (ValueError, TypeError):
            enrollment_version = 4

        if enrollment_version < 4:
            return {
                "success": False,
                "is_match": False,
                "confidence": 0.0,
                "threshold": threshold,
                "requires_re_registration": True,
                "message": (
                    "Face profile was enrolled with an outdated model version. "
                    "Please re-register your face profile in settings."
                ),
            }

        # Direct DB computation using stored vector(512)
        norm_ref = math.sqrt(sum(float(x) * float(x) for x in profile.embedding))
        norm_live = math.sqrt(sum(float(x) * float(x) for x in payload.face_embedding))
        if norm_ref == 0.0 or norm_live == 0.0:
            confidence = 0.0
        else:
            dot_prod = sum(float(a) * float(b) for a, b in zip(profile.embedding, payload.face_embedding))
            centroid_sim = float(dot_prod / (norm_ref * norm_live))
            centroid_sim = max(-1.0, min(1.0, centroid_sim))

            stored_poses = getattr(profile, "pose_embeddings", None)
            best_pose_sim = None
            if isinstance(stored_poses, list) and len(stored_poses) > 0:
                sims = []
                for p in stored_poses:
                    if isinstance(p, list) and len(p) == 512:
                        p_norm = math.sqrt(sum(float(x) * float(x) for x in p))
                        if p_norm > 0:
                            p_dot = sum(float(a) * float(b) for a, b in zip(p, payload.face_embedding))
                            s = float(p_dot / (p_norm * norm_live))
                            sims.append(max(-1.0, min(1.0, s)))
                if sims:
                    best_pose_sim = max(sims)

            if best_pose_sim is not None:
                confidence = max(centroid_sim, best_pose_sim)
            else:
                confidence = centroid_sim

        # Anti-spoof topological gate: depth feature similarity if available
        stored_depth = getattr(profile, "depth_features", None)
        if live_depth is not None and stored_depth is not None:
            if isinstance(stored_depth, list) and len(stored_depth) == len(live_depth):
                norm_d_ref = math.sqrt(sum(float(x) * float(x) for x in stored_depth))
                norm_d_live = math.sqrt(sum(float(x) * float(x) for x in live_depth))
                if norm_d_ref > 0 and norm_d_live > 0:
                    d_dot = sum(float(a) * float(b) for a, b in zip(stored_depth, live_depth))
                    depth_sim = max(-1.0, min(1.0, float(d_dot / (norm_d_ref * norm_d_live))))
                    if depth_sim < 0.40:
                        return {
                            "success": False,
                            "is_match": False,
                            "confidence": round(confidence, 4),
                            "threshold": threshold,
                            "message": "Face verification failed: Liveness and surface topology check failed (possible spoof).",
                        }

        is_match = confidence >= threshold

    # 3. Handle session attendance recording and verification attempts
    session_id_str = str(payload.lecture_session_id) if payload.lecture_session_id else ""
    is_test_class = (session_id_str == "TEST_MOCK_CLASS")

    window_id = None
    session = None
    if not is_test_class and session_id_str:
        try:
            session_uuid = UUID(session_id_str)
            session = resolve_session(db, session_uuid, student_id=student_id, now=now)
            if session:
                window = attendance_repository.get_open_window(db, session.id, "check_in")
                if not window:
                    window = attendance_repository.get_open_window(db, session.id, "random_check")
                if window:
                    window_id = window.id
        except Exception:
            pass

    # Geofence enforcement
    geo_inside = True
    distance_m = None
    geo_failure_reason = None

    if is_test_class:
        if payload.latitude is None or payload.longitude is None:
            geo_inside = False
            geo_failure_reason = "Missing GPS coordinates"
        else:
            distance_m = calculate_distance(payload.latitude, payload.longitude, 6.7951, 79.9009)
            geo_inside = distance_m <= 30.0
            if not geo_inside:
                geo_failure_reason = "Outside 30m geofence"
    elif session:
        if payload.latitude is None or payload.longitude is None:
            geo_inside = False
            geo_failure_reason = "Missing GPS coordinates"
        else:
            try:
                geo, venue = _venue_check(session, payload.latitude, payload.longitude)
                geo_inside = bool(geo.get("inside"))
                distance_m = geo.get("distance_meters")
                if not geo_inside:
                    geo_failure_reason = f"Outside geofence ({round(distance_m or 0)}m away)"
            except Exception as exc:
                geo_inside = False
                geo_failure_reason = f"Venue geofence error: {exc}"

    # Determine overall verification status
    overall_success = is_match and geo_inside
    attempt_status = AttemptStatus.success if overall_success else AttemptStatus.failed
    attempt_failure = None
    if not geo_inside:
        attempt_failure = geo_failure_reason
    elif not is_match:
        attempt_failure = "Face mismatch"

    # Log verification attempt in database if window exists
    if window_id:
        attendance_repository.log_attempt(db, {
            "id": attempt_id,
            "verification_window_id": window_id,
            "student_id": student_id,
            "attempt_number": 1,
            "used_face_verification": True,
            "used_location_check": bool(payload.latitude is not None and payload.longitude is not None),
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "distance_from_venue_meters": distance_m,
            "face_match_confidence": confidence,
            "status": attempt_status,
            "failure_reason": attempt_failure,
            "attempted_at": now,
        })

    # Location check failed: Reject immediately and do NOT record attendance
    if not geo_inside:
        return {
            "success": False,
            "is_match": is_match,
            "confidence": round(confidence, 4),
            "threshold": threshold,
            "attempt_id": str(attempt_id),
            "distance_meters": round(distance_m, 2) if distance_m is not None else None,
            "message": f"Location verification failed: {geo_failure_reason}. Attendance not recorded.",
        }

    # 4. If face match AND location inside geofence AND real lecture session, record attendance
    if is_match and session:
        record = attendance_repository.get_attendance_record(db, session.id, student_id)
        if not record:
            record = AttendanceRecord(
                id=uuid4(),
                lecture_session_id=session.id,
                student_id=student_id,
            )
            db.add(record)
        record.first_check_in_at = now
        late_threshold = int(getattr(session.course_offering, "late_threshold_minutes", 10) or 10)
        status_val = AttendanceStatus.late if now > session.scheduled_at + timedelta(minutes=late_threshold) else AttendanceStatus.present
        record.status = status_val
        db.commit()

    if not is_match:
        return {
            "success": False,
            "is_match": False,
            "confidence": round(confidence, 4),
            "threshold": threshold,
            "message": f"Face verification failed: Biometric mismatch with registered profile ({round(confidence * 100, 1)}% similarity, requires {int(threshold * 100)}%).",
        }

    return {
        "success": True,
        "is_match": True,
        "confidence": round(confidence, 4),
        "threshold": threshold,
        "attempt_id": str(attempt_id),
        "distance_meters": round(distance_m, 2) if distance_m is not None else None,
        "message": "Face verified successfully within lecture hall geofence. Attendance recorded.",
    }
