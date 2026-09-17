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


class RegisterRequest(BaseModel):
    student_id: str
    face_embedding: list[float] = Field(
        ...,
        min_length=192,
        max_length=192,
        description="192-dimensional MobileFaceNet embedding vector",
    )
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0)


@router.post("/internal/verify", dependencies=[Depends(verify_internal_key)])
def verify_face(payload: VerifyRequest, db: Session = Depends(get_db)):
    try:
        return matching_service.verify_face(
            db,
            payload.student_id,
            live_embedding=payload.face_embedding,
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
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
