from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from shared_core.models.enums import AttemptStatus, AttendanceStatus
from shared_core.schemas.events import FaceVerificationTask
from shared_core.models.identity import Student
from app.clients import scheduling_client
from app.repositories import attendance_repository
from app.utils.geofence import geofence_check
from app.rabbitmq.publisher import publish_verification_task
from shared_core.audit import audit


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
    attendance_repository.schedule_check_in_window(db, session, duration_mins=15)
    if offering.get("random_check_enabled"):
        attendance_repository.schedule_random_window(db, session, int(offering.get("random_check_window_minutes", 10)))
    return session


def end_session(db: Session, session_id: UUID, current_user):
    session = attendance_repository.get_session(db, session_id)
    if not session: return None
    if str(getattr(current_user.role, "value", current_user.role)) == "lecturer" and session.course_offering.lecturer_id != current_user.id:
        raise HTTPException(403, "You are not assigned to this offering")
    return attendance_repository.close_session(db, session_id)


def _window_payload(window, include_identity: bool = True):
    if not window: return None
    payload={"id": window.id, "window_type": getattr(window.window_type,"value",window.window_type), "is_active": window.is_active, "opened_at": window.actual_opened_at, "closed_at": window.actual_closed_at}
    if not include_identity:
        payload.pop("id",None)
    return payload

def get_active_windows(db: Session, lecture_session_id: UUID, student_id: UUID | None = None):
    check = attendance_repository.get_open_window(db, lecture_session_id, "check_in")
    random_window = attendance_repository.get_open_window(db, lecture_session_id, "random_check")
    return {
        "check_in_window": _window_payload(check),
        "random_check_active": bool(random_window),
        # The exact random window identifier is only exposed while the window is open.
        "random_check_window": _window_payload(random_window) if random_window and student_id else None,
    }


def record_check_in(db: Session, student_id: UUID, payload):
    session = _assert_student_enrolled(db, student_id, payload.lecture_session_id)
    window = attendance_repository.get_open_window(db, session.id, "check_in")
    if not window: raise HTTPException(400, "No active check-in window")
    record = attendance_repository.get_attendance_record(db, session.id, student_id)
    if record and record.first_check_in_at:
        raise HTTPException(409, "Attendance check-in already recorded")
    geo, _ = _venue_check(session, payload.latitude, payload.longitude)
    now = datetime.now(timezone.utc)
    if not geo["inside"]:
        attendance_repository.log_attempt(db, {
            "verification_window_id": window.id, "student_id": student_id, "used_location_check": True,
            "location_method": "gps_geofence", "latitude": payload.latitude, "longitude": payload.longitude,
            "distance_from_venue_meters": geo.get("distance_meters"), "status": AttemptStatus.failed,
            "failure_reason": "Outside geofence", "attempted_at": now,
        })
        raise HTTPException(400, "Location check failed: outside geofence")
    late_threshold = int(session.course_offering.late_threshold_minutes or 10)
    status = AttendanceStatus.late if now > session.scheduled_at + timedelta(minutes=late_threshold) else AttendanceStatus.present
    record = attendance_repository.create_or_get_record(db, session.id, student_id)
    record.first_check_in_at = now
    record.status = status
    db.add(record)
    db.commit(); db.refresh(record)
    return attendance_repository.log_attempt(db, {
        "verification_window_id": window.id, "student_id": student_id, "used_location_check": True,
        "location_method": "gps_geofence", "latitude": payload.latitude, "longitude": payload.longitude,
        "distance_from_venue_meters": geo.get("distance_meters"), "status": AttemptStatus.success,
        "attempted_at": now,
    })


async def record_random_check(db: Session, student_id: UUID, payload):
    session = _assert_student_enrolled(db, student_id, payload.lecture_session_id)
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
        return {"status": "rejected", "attempt_id": attempt.id, "reason": "outside_geofence"}

    task = FaceVerificationTask(
        event_id=uuid4(), attempt_id=attempt_id, student_id=student_id, verification_window_id=active.id,
        face_image_base64=payload.face_image_base64, latitude=payload.latitude, longitude=payload.longitude,
    )
    try:
        await publish_verification_task(task)
    except Exception as exc:
        attendance_repository.log_attempt(db, {
            "id": attempt_id, "verification_window_id": active.id, "student_id": student_id,
            "used_face_verification": True, "used_location_check": True, "location_method": "gps_geofence",
            "latitude": payload.latitude, "longitude": payload.longitude,
            "distance_from_venue_meters": geo.get("distance_meters"), "status": AttemptStatus.failed,
            "failure_reason": f"Queue unavailable: {exc}",
        })
        raise HTTPException(503, "Face verification queue unavailable") from exc
    return {"status": "processing", "attempt_id": attempt_id}


def get_student_attendance(db, student_id): return attendance_repository.get_attendance_records(db, student_id=student_id)
def get_attendance_attempts(db, record_id): return attendance_repository.get_attempts_for_record(db, record_id)
def get_recent_attempts(db, offering_id=None): return attendance_repository.get_recent_attempts(db, offering_id)


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
