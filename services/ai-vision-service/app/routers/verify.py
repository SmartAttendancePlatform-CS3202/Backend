from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from shared_core.auth.rbac import verify_internal_key
from shared_core.db.session import get_db
from sqlalchemy.orm import Session
from app.services import matching_service

router = APIRouter(tags=["verification"])

class VerifyRequest(BaseModel):
    student_id: str
    face_image_base64: str = Field(min_length=100, max_length=6_800_000)

class RegisterRequest(VerifyRequest):
    pass

@router.post("/internal/verify", dependencies=[Depends(verify_internal_key)])
def verify_face(payload: VerifyRequest, db: Session = Depends(get_db)):
    try: return matching_service.verify_face(db, payload.student_id, payload.face_image_base64)
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc

@router.post("/internal/register", dependencies=[Depends(verify_internal_key)], status_code=201)
def register_face(payload: RegisterRequest, db: Session = Depends(get_db)):
    try: return matching_service.register_face(db, payload.student_id, payload.face_image_base64)
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc
