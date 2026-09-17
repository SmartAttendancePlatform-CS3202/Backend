from typing import List
import httpx
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from prometheus_client import Counter
from sqlalchemy.orm import Session
from shared_core.auth.rbac import require_role
from shared_core.db.session import get_db
from shared_core.models.identity import User
from app.clients import ai_vision_client

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
REGISTER_FACE_ATTEMPTS = Counter("register_face_attempt_count", "Face registration attempts", ["reason"])


class RegisterFaceRequest(BaseModel):
    face_embedding: List[float] = Field(
        ...,
        min_length=192,
        max_length=192,
        description="192-dimensional MobileFaceNet embedding vector",
    )
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0)


@router.post("/register-face", status_code=status.HTTP_201_CREATED)
def register_face(
    data: RegisterFaceRequest,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    REGISTER_FACE_ATTEMPTS.labels(reason="attempt").inc()
    try:
        res = ai_vision_client.register_face(
            student_id=str(current_user.id),
            face_embedding=data.face_embedding,
            quality_score=data.quality_score,
        )
        REGISTER_FACE_ATTEMPTS.labels(reason="success").inc()
        return res
    except httpx.HTTPStatusError as exc:
        REGISTER_FACE_ATTEMPTS.labels(reason="failed").inc()
        raise HTTPException(
            exc.response.status_code,
            f"Face registration failed: {exc.response.text}",
        ) from exc
    except httpx.HTTPError as exc:
        REGISTER_FACE_ATTEMPTS.labels(reason="failed").inc()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI Vision service unavailable",
        ) from exc
