from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared_core.db.session import get_db
from shared_core.auth.rbac import verify_internal_key
from app.services import matching_service

router = APIRouter(tags=["verification"])


class VerifyRequest(BaseModel):
    student_id: str
    face_image_base64: str


class RegisterRequest(BaseModel):
    student_id: str
    face_image_base64: str


@router.post(
    "/verify",
    dependencies=[Depends(verify_internal_key)],
    summary="Verify a face against a registered student embedding",
)
def verify_face(
    payload: VerifyRequest,
    db: Session = Depends(get_db),
):
    try:
        return matching_service.verify_face(db, payload.student_id, payload.face_image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/register",
    dependencies=[Depends(verify_internal_key)],
    status_code=status.HTTP_201_CREATED,
    summary="Register a student's face embedding",
)
def register_face(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    try:
        return matching_service.register_face(db, payload.student_id, payload.face_image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
