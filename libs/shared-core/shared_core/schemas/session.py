from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CheckInRequest(BaseModel):
    lecture_session_id: UUID
    latitude: float
    longitude: float


class RandomCheckRequest(BaseModel):
    verification_window_id: UUID
    latitude: float
    longitude: float
    face_image_base64: str


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
