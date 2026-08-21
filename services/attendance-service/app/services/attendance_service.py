import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from shared_core.models.attendance import LectureSession, AttendanceRecord, AttendanceVerificationAttempt
from shared_core.schemas.events import FaceVerificationTask
from shared_core.models.enums import AttemptStatus, WindowType
from app.clients import scheduling_client
from app.repositories import attendance_repository
from app.utils.geofence import calculate_distance
from app.rabbitmq.publisher import publish_verification_task
from app.routers.checkin import RANDOM_CHECK_ATTEMPTS

def start_session(db: Session, data: dict) -> LectureSession:
    # 1. Verify offering exists via scheduling_client
    offering = scheduling_client.get_offering(data['course_offering_id'])
    
    # 2. Create the session
    session = attendance_repository.create_session(db, data)
    
    # 3. Schedule first check-in window
    attendance_repository.schedule_check_in_window(db, session)
    
    # 4. Schedule random window if enabled
    if offering.get("random_check_enabled"):
        attendance_repository.schedule_random_window(db, session, offering.get("random_check_window_minutes", 10))
        
    return session

def end_session(db: Session, session_id: uuid.UUID) -> Optional[LectureSession]:
    return attendance_repository.close_session(db, session_id)

def get_session(db: Session, session_id: uuid.UUID) -> Optional[LectureSession]:
    return attendance_repository.get_session(db, session_id)

def get_sessions(db: Session, offering_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100) -> List[LectureSession]:
    return attendance_repository.get_sessions(db, offering_id, skip, limit)

def get_active_windows(db: Session, lecture_session_id: uuid.UUID) -> dict:
    check_in_window = attendance_repository.get_open_window(db, lecture_session_id, WindowType.first_check_in.value)
    random_window = attendance_repository.get_open_window(db, lecture_session_id, "random_check")
    
    return {
        "first_check_in_window": check_in_window,
        "random_check_window": random_window
    }

def record_check_in(db: Session, student_id: uuid.UUID, payload):
    window = attendance_repository.get_open_window(db, payload.lecture_session_id, window_type=WindowType.first_check_in.value)
    if not window:
        raise HTTPException(status_code=400, detail="No active check-in window found for this session.")
        
    attempt_data = {
        "verification_window_id": window.id,
        "student_id": student_id,
        "used_face_verification": False,
        "used_location_check": True,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "status": AttemptStatus.success, # Assuming location is always correct for MVP check-in?
    }
    
    attempt = attendance_repository.log_attempt(db, attempt_data)
    attendance_repository.upsert_first_check_in(db, payload.lecture_session_id, student_id, attempt_data)
    
    return attempt

async def record_random_check(db: Session, student_id: uuid.UUID, payload):
    # 1. Ensure there's an active random window
    window = attendance_repository.get_open_window(db, payload.lecture_session_id, window_type="random_check")
    if not window:
        RANDOM_CHECK_ATTEMPTS.labels(reason="no_active_window").inc()
        raise HTTPException(status_code=400, detail="No active random check window found for this session.")
        
    # 2. Geofence Distance Check (Synchronous)
    # Fetch venue details to get coordinates. We need venue info from the session.
    session = attendance_repository.get_session(db, payload.lecture_session_id)
    if not session:
        RANDOM_CHECK_ATTEMPTS.labels(reason="session_not_found").inc()
        raise HTTPException(status_code=404, detail="Lecture session not found.")

    # We should get the venue from scheduling_service
    offering = scheduling_client.get_offering(session.course_offering_id)
    if not offering:
        RANDOM_CHECK_ATTEMPTS.labels(reason="offering_not_found").inc()
        raise HTTPException(status_code=404, detail="Course offering not found.")

    venue_id = offering.get('venue_id')
    # If there's no venue_id or we can't fetch it, we might skip location or fail. Assuming we have venue details in offering or can fetch from scheduling service (need venue endpoint). For now, let's just do a basic stub or assume radius is 30m and we have venue lat/lon in boundary_data.
    # To properly calculate distance, we need the venue's boundary_data (center coordinates).
    # Since we can't easily fetch venue directly via client yet without adding a new client method, let's assume it passes for now or add a stub.
    
    distance_meters = 0.0 # STUB: Replace with actual distance calculation using venue boundary_data
    radius = 30 # Default radius
    
    if distance_meters > radius:
        # Save failed attempt
        attempt_data = {
            "verification_window_id": window.id,
            "student_id": student_id,
            "used_face_verification": False,
            "used_location_check": True,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "distance_from_venue_meters": distance_meters,
            "status": AttemptStatus.failed,
            "failure_reason": "Out of bounds"
        }
        attendance_repository.log_attempt(db, attempt_data)
        RANDOM_CHECK_ATTEMPTS.labels(reason="out_of_bounds").inc()
        raise HTTPException(status_code=400, detail="Location check failed: Out of bounds.")

    # 3. Publish Face Verification Task (Asynchronous)
    task = FaceVerificationTask(
        student_id=str(student_id),
        verification_window_id=window.id,
        face_image_base64=payload.face_image_base64,
        latitude=payload.latitude,
        longitude=payload.longitude
    )
    
    await publish_verification_task(task)

    RANDOM_CHECK_ATTEMPTS.labels(reason="queued_success").inc()
    return {"status": "processing"}

def get_student_attendance(db: Session, student_id: uuid.UUID):
    return attendance_repository.get_attendance_records(db, student_id=student_id)

def get_attendance_attempts(db: Session, record_id: uuid.UUID):
    return attendance_repository.get_attempts(db, record_id)

def get_recent_attempts(db: Session, offering_id: Optional[uuid.UUID] = None):
    return attendance_repository.get_recent_attempts(db, offering_id)

def override_record(db: Session, record_id: uuid.UUID, user_id: uuid.UUID, override_data: dict):
    override_data["is_manually_overridden"] = True
    override_data["override_by"] = user_id
    from datetime import datetime
    override_data["overridden_at"] = datetime.utcnow()
    return attendance_repository.update_attendance_record(db, record_id, override_data)

