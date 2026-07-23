from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class CheckInRequest(BaseModel):
    lecture_session_id: UUID
    latitude: float
    longitude: float

class RandomCheckRequest(BaseModel):
    verification_window_id: UUID
    latitude: float
    longitude: float
    face_image_base64: str

class SessionCreate(BaseModel):
    course_offering_id: UUID
    verification_method_override: Optional[str] = None
    notes: Optional[str] = None

class LectureSessionOut(BaseModel):
    id: UUID
    course_offering_id: UUID
    venue_id: Optional[UUID] = None
    verification_method_override: Optional[str] = None
    scheduled_at: datetime
    duration_mins: int
    status: str
    held_at: Optional[datetime] = None
    notes: Optional[str] = None
    session_number: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class VerificationWindowOut(BaseModel):
    id: UUID
    lecture_session_id: UUID
    window_type: str
    scheduled_open_at: datetime
    scheduled_close_at: datetime
    actual_opened_at: Optional[datetime] = None
    actual_closed_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AttendanceRecordOut(BaseModel):
    id: UUID
    lecture_session_id: UUID
    student_id: UUID
    status: str
    first_check_in_at: Optional[datetime] = None
    random_check_completed_at: Optional[datetime] = None
    flag_reason: Optional[str] = None
    is_manually_overridden: bool
    override_by: Optional[UUID] = None
    override_reason: Optional[str] = None
    overridden_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AttemptOut(BaseModel):
    id: UUID
    verification_window_id: UUID
    student_id: UUID
    attempt_number: int
    used_face_verification: bool
    used_location_check: bool
    location_method: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_from_venue_meters: Optional[float] = None
    wifi_ssid_detected: Optional[str] = None
    face_match_confidence: Optional[float] = None
    status: str
    failure_reason: Optional[str] = None
    device_info: Optional[dict] = None
    attempted_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
