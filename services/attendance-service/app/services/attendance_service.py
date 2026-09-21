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
from app.utils.geofence import geofence_check, calculate_distance
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
    session = attendance_repository.get_session(db, lecture_session_id)
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
                pass

    return {
        "check_in_window": _window_payload(check),
        "random_check_active": bool(random_window),
        # The exact random window identifier is only exposed while the window is open.
        "random_check_window": _window_payload(random_window) if random_window and student_id else None,
        "venue_geofence": venue_geofence,
    }


def verify_location_precheck(db: Session, student_id: UUID, payload):
    now = datetime.now(timezone.utc)
    session_id_str = str(payload.lecture_session_id)
    is_test_class = (session_id_str == "TEST_MOCK_CLASS")

    if is_test_class:
        dist = calculate_distance(payload.latitude, payload.longitude, 6.7951, 79.9009)
        inside = dist <= 30.0
        return {
            "success": True,
            "inside": inside,
            "distance_meters": round(dist, 2),
            "radius_meters": 30,
            "venue_name": "Seminar Room (Mock)",
            "message": "Within 30m geofence" if inside else f"Outside 30m geofence ({round(dist)}m away, must be <= 30m)",
        }

    try:
        session_uuid = UUID(session_id_str)
    except ValueError:
        raise HTTPException(400, "Invalid lecture session ID format")

    session = attendance_repository.get_session(db, session_uuid)
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
        "message": "Within geofence" if inside else f"Outside geofence ({round(dist or 0)}m away, must be <= {round(radius)}m)",
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
        enrollment_version_raw = getattr(profile, "enrollment_version", 3)
        try:
            if isinstance(enrollment_version_raw, (int, float, str)):
                enrollment_version = int(enrollment_version_raw)
            else:
                enrollment_version = 3
        except (ValueError, TypeError):
            enrollment_version = 3

        if enrollment_version < 3:
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

        # Direct DB computation using stored vector(192)
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
                    if isinstance(p, list) and len(p) == 192:
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
            session = attendance_repository.get_session(db, session_uuid)
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
            geo_inside = (distance_m <= 30.0)
            if not geo_inside:
                geo_failure_reason = f"Outside 30m geofence ({round(distance_m)}m away, must be <= 30m)"
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


