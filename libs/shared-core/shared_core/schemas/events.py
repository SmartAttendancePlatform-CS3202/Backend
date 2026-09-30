from uuid import UUID
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class FaceVerificationTask(BaseModel):
    event_id: UUID
    attempt_id: UUID
    student_id: UUID
    verification_window_id: UUID
    face_embedding: list[float] = Field(min_length=192, max_length=192, description="192-D MobileFaceNet embedding vector")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class FaceVerificationResult(BaseModel):
    event_id: UUID
    attempt_id: UUID
    student_id: UUID
    verification_window_id: UUID
    face_match: bool
    confidence: float = Field(ge=-1, le=1)
    processing_ms: int = Field(ge=0)
    status: Literal["completed", "failed"] = "completed"
    failure_reason: str | None = None
