from uuid import UUID
from pydantic import BaseModel

class FaceVerificationTask(BaseModel):
    student_id: str
    verification_window_id: UUID
    face_image_base64: str
    latitude: float
    longitude: float

class FaceVerificationResult(BaseModel):
    student_id: str
    verification_window_id: UUID
    latitude: float
    longitude: float
    is_match: bool
    confidence: float
