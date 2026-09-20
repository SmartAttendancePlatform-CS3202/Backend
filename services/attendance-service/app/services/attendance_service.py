from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
from typing import Optional
import math
import os
from fastapi import HTTPException
from sqlalchemy.orm import Session
from shared_core.models.enums import AttemptStatus, AttendanceStatus
from shared_core.schemas.events import FaceVerificationTask
from shared_core.models.identity import Student
from shared_core.models.vision import FaceProfile
from shared_core.models.attendance import AttendanceRecord
from app.clients import scheduling_client, ai_vision_client
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
    return session

def trigger_random_window(db: Session, session_id: UUID, current_user):
    session = attendance_repository.get_session(db, session_id)
    if not session: raise HTTPException(404, "Lecture session not found")
    if str(getattr(current_user.role, "value", current_user.role)) == "lecturer" and session.course_offering.lecturer_id != current_user.id:
        raise HTTPException(403, "You are not assigned to this offering")
    if getattr(session.status, "value", session.status) != "ongoing":
        raise HTTPException(400, "Session is not ongoing")
    
    # Check if a random window already exists for this session
    existing_window = next((w for w in session.verification_windows if getattr(w.window_type, "value", w.window_type) == "random_check"), None)
    if existing_window:
        raise HTTPException(400, "A random check-in window has already been triggered for this session")
        
    return attendance_repository.schedule_random_window(db, session, window_minutes=10)


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



async def record_check_in(db: Session, student_id: UUID, payload):
    session = _assert_student_enrolled(db, student_id, payload.lecture_session_id)
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
    active = attendance_repository.get_open_window(db, session.id, "random_check")
    if not active or active.id != payload.verification_window_id:
        raise HTTPException(400, "No active random verification window")
    
    now = datetime.now(timezone.utc)
    attempt_id = uuid4()

    task = FaceVerificationTask(
        event_id=uuid4(), attempt_id=attempt_id, student_id=student_id, verification_window_id=active.id,
        face_embedding=payload.face_embedding, latitude=payload.latitude, longitude=payload.longitude,
    )
    try:
        await publish_verification_task(task)
    except Exception as exc:
        attendance_repository.log_attempt(db, {
            "id": attempt_id, "verification_window_id": active.id, "student_id": student_id,
            "used_face_verification": True, "used_location_check": False,
            "latitude": payload.latitude, "longitude": payload.longitude,
            "status": AttemptStatus.failed,
            "failure_reason": f"Queue unavailable: {exc}", "attempted_at": now,
        })
        raise HTTPException(503, "Face verification queue unavailable") from exc
    return {"status": "processing", "attempt_id": attempt_id}


def get_student_attendance(db, student_id): return attendance_repository.get_attendance_records(db, student_id=student_id)

def get_records(db, session_id=None, student_id=None): return attendance_repository.get_attendance_records(db, session_id=session_id, student_id=student_id)
def get_attendance_attempts(db, record_id): return attendance_repository.get_attempts_for_record(db, record_id)
def get_recent_attempts(db, offering_id=None): return attendance_repository.get_recent_attempts(db, offering_id)

def get_sessions(db, offering_id=None, skip=0, limit=100, status=None): return attendance_repository.get_sessions(db, offering_id, skip, limit, status)

def get_session(db, session_id): return attendance_repository.get_session(db, session_id)


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
    """
    Synchronously verifies a student's live face embedding against their
    registered profile in the database, records attendance if matched and session exists,
    and logs verification attempts.
    """
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
    try:
        match_result = ai_vision_client.verify_face(str(student_id), payload.face_embedding)
    except Exception:
        # Fallback to direct in-memory cosine similarity against stored DB profile
        pass

    if match_result and "is_match" in match_result:
        is_match = bool(match_result.get("is_match"))
        confidence = float(match_result.get("confidence", 0.0))
    else:
        # Direct DB computation using stored vector(192)
        norm_ref = math.sqrt(sum(float(x) * float(x) for x in profile.embedding))
        norm_live = math.sqrt(sum(float(x) * float(x) for x in payload.face_embedding))
        if norm_ref == 0.0 or norm_live == 0.0:
            confidence = 0.0
        else:
            dot_prod = sum(float(a) * float(b) for a, b in zip(profile.embedding, payload.face_embedding))
            centroid_sim = float(dot_prod / (norm_ref * norm_live))
            confidence = max(-1.0, min(1.0, centroid_sim))

            stored_poses = getattr(profile, "pose_embeddings", None)
            if isinstance(stored_poses, list) and len(stored_poses) > 0:
                sims = []
                for p in stored_poses:
                    if isinstance(p, list) and len(p) == 192:
                        p_norm = math.sqrt(sum(float(x) * float(x) for x in p))
                        if p_norm > 0:
                            p_dot = sum(float(a) * float(b) for a, b in zip(p, payload.face_embedding))
                            s = float(p_dot / (p_norm * norm_live))
                            sims.append(max(-1.0, min(1.0, s)))
                if sims:
                    confidence = 0.6 * confidence + 0.4 * max(sims)
        is_match = confidence >= threshold

    # 3. Handle session attendance recording and verification attempts
    session_id_str = str(payload.lecture_session_id) if payload.lecture_session_id else ""
    is_test_class = (session_id_str == "TEST_MOCK_CLASS")

    window_id = None
    session = None
    if not is_test_class and session_id_str:
        try:
            session_uuid = UUID(session_id_str)
            session = attendance_repository.get_session(db, session_uuid)
            if session:
                window = attendance_repository.get_open_window(db, session.id, "check_in")
                if not window:
                    window = attendance_repository.get_open_window(db, session.id, "random_check")
                if window:
                    window_id = window.id
        except Exception:
            pass

    # Log verification attempt in database if window exists
    if window_id:
        attendance_repository.log_attempt(db, {
            "id": attempt_id,
            "verification_window_id": window_id,
            "student_id": student_id,
            "attempt_number": 1,
            "used_face_verification": True,
            "used_location_check": bool(payload.latitude and payload.longitude),
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "face_match_confidence": confidence,
            "status": AttemptStatus.success if is_match else AttemptStatus.failed,
            "failure_reason": None if is_match else "Face mismatch",
            "attempted_at": now,
        })

    # 4. If match and real lecture session, record attendance
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
        "message": "Face verified successfully against database profile. Attendance recorded.",
    }

