"""
Core orchestration logic. This is where the two-phase (soon three-phase)
check flow actually lives:
  1. record_check_in       -> location-only tick at lecture start
  2. record_random_check   -> face + location, verified via ai-vision-service
Both write to attendance_verification_attempts and roll up into
attendance_records (see university_attendance_schema.sql).
"""
from uuid import UUID

from app.clients import ai_vision_client, scheduling_client
from app.repositories import attendance_repository


def start_session(course_offering_id: UUID):
    offering = scheduling_client.get_offering(course_offering_id)
    session = attendance_repository.create_session(offering)
    attendance_repository.schedule_check_in_window(session)
    if offering["random_check_enabled"]:
        attendance_repository.schedule_random_window(session, offering["random_check_window_minutes"])
    return session


def end_session(session_id: UUID):
    return attendance_repository.close_session(session_id)


def record_check_in(student_id: str, payload):
    window = attendance_repository.get_open_window(payload.lecture_session_id, window_type="check_in")
    attempt = attendance_repository.log_attempt(
        window_id=window["id"],
        student_id=student_id,
        used_face_verification=False,
        used_location_check=True,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    attendance_repository.upsert_first_check_in(payload.lecture_session_id, student_id, attempt)
    return attempt


def record_random_check(student_id: str, payload):
    face_result = ai_vision_client.verify_face(student_id, payload.face_image_base64)
    attempt = attendance_repository.log_attempt(
        window_id=payload.verification_window_id,
        student_id=student_id,
        used_face_verification=True,
        used_location_check=True,
        latitude=payload.latitude,
        longitude=payload.longitude,
        face_match_confidence=face_result["confidence"],
        status="success" if face_result["is_match"] else "failed",
    )
    attendance_repository.update_random_check_status(payload.verification_window_id, student_id, attempt)
    return attempt


def get_offering_report(course_offering_id: UUID):
    return attendance_repository.get_offering_report(course_offering_id)
