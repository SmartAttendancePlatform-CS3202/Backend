from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from shared_core.auth.rbac import verify_internal_key
from shared_core.db.session import get_db
from sqlalchemy.orm import Session
from app.services import matching_service

router = APIRouter(tags=["verification"])


class VerifyRequest(BaseModel):
    student_id: str
    face_embedding: list[float] = Field(
        ...,
        min_length=192,
        max_length=192,
        description="192-dimensional MobileFaceNet embedding vector",
    )
    depth_features: list[float] | None = Field(
        default=None,
        description="Optional 48D pseudo-depth features for anti-spoof topology check",
    )


class RegisterRequest(BaseModel):
    student_id: str
    face_embedding: list[float] = Field(
        ...,
        min_length=192,
        max_length=192,
        description="192-dimensional MobileFaceNet centroid embedding vector",
    )
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    pose_embeddings: list[list[float]] | None = Field(
        default=None,
        description="5 pose embeddings (Center, Left, Right, Up, Down)",
    )
    depth_features: list[float] | None = Field(
        default=None,
        description="48-dimensional depth feature vector",
    )
    enrollment_metadata: dict | None = Field(
        default=None,
        description="Capture metadata including Euler angles and quality scores",
    )


@router.post("/internal/verify", dependencies=[Depends(verify_internal_key)])
def verify_face(payload: VerifyRequest, db: Session = Depends(get_db)):
    try:
        return matching_service.verify_face(
            db,
            payload.student_id,
            live_embedding=payload.face_embedding,
            live_depth_features=payload.depth_features,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.post(
    "/internal/register",
    dependencies=[Depends(verify_internal_key)],
    status_code=status.HTTP_201_CREATED,
)
def register_face(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return matching_service.register_face(
            db,
            payload.student_id,
            embedding=payload.face_embedding,
            quality_score=payload.quality_score,
            pose_embeddings=payload.pose_embeddings,
            depth_features=payload.depth_features,
            enrollment_metadata=payload.enrollment_metadata,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
