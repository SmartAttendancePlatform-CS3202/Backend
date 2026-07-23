from uuid import UUID
from pydantic import BaseModel

class CheckInRequest(BaseModel):
    lecture_session_id: UUID
    latitude: float
    longitude: float

class RandomCheckRequest(BaseModel):
    verification_window_id: UUID
    latitude: float
    longitude: float
    face_image_base64: str
