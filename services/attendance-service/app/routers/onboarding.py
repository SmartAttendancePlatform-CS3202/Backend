import os
from datetime import datetime, timezone
from typing import List, Optional
import httpx
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from prometheus_client import Counter
from sqlalchemy.orm import Session
from shared_core.auth.rbac import require_role
from shared_core.config import get_settings
from shared_core.db.session import get_db
from shared_core.models.identity import User
from shared_core.models.vision import FaceProfile

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
REGISTER_FACE_ATTEMPTS = Counter("register_face_attempt_count", "Face registration attempts", ["reason"])

class RegisterFaceRequest(BaseModel):
    face_embedding: Optional[List[float]] = None
    face_image_base64: Optional[str] = Field(default=None, max_length=6_800_000)

@router.post("/register-face")
async def register_face(
    data: RegisterFaceRequest,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db)
):
    REGISTER_FACE_ATTEMPTS.labels(reason="attempt").inc()

    # 1. Direct 192-dimensional embedding registration
    if data.face_embedding is not None:
        if len(data.face_embedding) != 192:
            REGISTER_FACE_ATTEMPTS.labels(reason="failed").inc()
            raise HTTPException(
                status_code=400,
                detail=f"Expected 192-dimensional vector, got {len(data.face_embedding)}"
            )

        # Deactivate any previous active profile for the student
        existing = (
            db.query(FaceProfile)
            .filter(FaceProfile.student_id == current_user.id, FaceProfile.is_active.is_(True))
            .first()
        )
        if existing:
            existing.is_active = False
            existing.superseded_at = datetime.now(timezone.utc)

        new_profile = FaceProfile(
            student_id=current_user.id,
            embedding=data.face_embedding,
            reference_photo_url=f"https://storage.example.com/faces/{current_user.id}.jpg",
            quality_score=1.0,
            is_active=True,
        )
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)

        REGISTER_FACE_ATTEMPTS.labels(reason="success").inc()
        return {
            "status": "success",
            "student_id": str(current_user.id),
            "message": "192-dimensional face embedding registered successfully."
        }

    # 2. Server-side DeepFace extraction from base64 image (if provided)
    if data.face_image_base64:
        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{os.environ.get('AI_VISION_SERVICE_URL', 'http://ai-vision-service:8000')}/internal/register",
                    json={"student_id": str(current_user.id), "face_image_base64": data.face_image_base64},
                    headers={"X-Internal-Key": settings.internal_api_key},
                )
                resp.raise_for_status()
                REGISTER_FACE_ATTEMPTS.labels(reason="success").inc()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            REGISTER_FACE_ATTEMPTS.labels(reason="failed").inc()
            raise HTTPException(exc.response.status_code, f"Face registration failed: {exc.response.text}") from exc
        except httpx.HTTPError as exc:
            REGISTER_FACE_ATTEMPTS.labels(reason="failed").inc()
            raise HTTPException(503, "AI Vision service unavailable") from exc

    REGISTER_FACE_ATTEMPTS.labels(reason="failed").inc()
    raise HTTPException(status_code=422, detail="Either face_embedding or face_image_base64 must be provided.")
