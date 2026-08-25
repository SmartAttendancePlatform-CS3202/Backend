from uuid import UUID
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class FaceVerificationTask(BaseModel):
    event_id: UUID
    attempt_id: UUID
    student_id: UUID
    verification_window_id: UUID
    face_image_base64: str = Field(min_length=100, max_length=6_800_000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    @field_validator("face_image_base64")
    @classmethod
    def validate_image_payload(cls, value: str) -> str:
        raw = value.split(',', 1)[1] if ',' in value else value
        import base64, binascii
        try:
            decoded = base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Invalid base64 image") from exc
        if len(decoded) > 5_000_000:
            raise ValueError("Face image exceeds 5 MB")
        return value


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
