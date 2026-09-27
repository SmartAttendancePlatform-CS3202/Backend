from typing import List, Optional
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
        min_length=512,
        max_length=512,
        description="512-dimensional centroid FaceNet embedding vector",
    )
    pose_embeddings: Optional[List[List[float]]] = Field(
        default=None,
        description="List of 512D embeddings captured across guided poses (Center, Left, Right, Up, Down)",
    )
    depth_features: Optional[List[float]] = Field(
        default=None,
        description="48D pseudo-depth and contour geometry feature vector",
    )
    enrollment_metadata: Optional[dict] = Field(
        default=None,
        description="Pose Euler angles, lighting scores, and capture quality metrics",
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
            pose_embeddings=data.pose_embeddings,
            depth_features=data.depth_features,
            enrollment_metadata=data.enrollment_metadata,
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
