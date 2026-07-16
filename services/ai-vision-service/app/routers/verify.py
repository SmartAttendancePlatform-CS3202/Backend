from fastapi import APIRouter
from pydantic import BaseModel

from app.services import matching_service

router = APIRouter(tags=["verify"])


class VerifyRequest(BaseModel):
    student_id: str
    face_image_base64: str


class VerifyResponse(BaseModel):
    is_match: bool
    confidence: float


@router.post("/verify", response_model=VerifyResponse)
def verify(payload: VerifyRequest):
    """Called internally by attendance-service during a random check.
    Not exposed to the mobile app directly."""
    return matching_service.verify(payload.student_id, payload.face_image_base64)


@router.post("/register")
def register(student_id: str, face_image_base64: str):
    """Called during mobile onboarding to create the student's
    face_profiles reference embedding."""
    return matching_service.register(student_id, face_image_base64)
