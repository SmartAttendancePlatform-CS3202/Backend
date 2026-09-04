from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from shared_core.auth.rbac import verify_internal_key
from shared_core.db.session import get_db
from sqlalchemy.orm import Session
from app.services.matching_service import register_face as register_face_service
from app.services.matching_service import verify_face as verify_face_service

router = APIRouter(tags=["verification"])

class VerifyRequest(BaseModel):
    student_id: str
    face_image_base64: Optional[str] = Field(default=None, max_length=6_800_000)
    face_embedding: Optional[List[float]] = None

class RegisterRequest(VerifyRequest):
    pass

@router.post("/internal/verify", dependencies=[Depends(verify_internal_key)])
def verify_face(payload: VerifyRequest, db: Session = Depends(get_db)):
    try:
        return verify_face_service(
            db,
            payload.student_id,
            live_image_base64=payload.face_image_base64,
            live_embedding=payload.face_embedding,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@router.post("/internal/register", dependencies=[Depends(verify_internal_key)], status_code=201)
def register_face(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return register_face_service(
            db,
            payload.student_id,
            image_base64=payload.face_image_base64,
            embedding=payload.face_embedding,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
