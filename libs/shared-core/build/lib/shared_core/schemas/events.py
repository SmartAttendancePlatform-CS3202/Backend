from uuid import UUID
from pydantic import BaseModel

class FaceVerificationTask(BaseModel):
    student_id: str
    verification_window_id: UUID
    face_image_base64: str
    latitude: float
    longitude: float
